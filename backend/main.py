from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Union
import asyncio
import logging
from google.cloud import speech

from backend.models import TriageRequest, FollowUpResponse, TriageCompleteResponse, EmergencyResponse, DoctorSearchRequest, DoctorSearchResponse, SessionState
from backend.triage_logic import check_red_flags, apply_specialist_backstop, call_gemini_triage
from backend.translation_logic import translate_text, async_translate_text
from backend.places_logic import search_nearby_doctors
from backend.auth_logic import verify_id_token
from backend.firestore_logic import get_session, update_session

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CarepathAI Triage API", version="1.0.0")

# Configure CORS Middleware (crucial for local development & production with Firebase)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to specific Firebase domains if preferred
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/triage", response_model=Union[FollowUpResponse, TriageCompleteResponse, EmergencyResponse])
async def triage(request: TriageRequest, uid: str = Depends(verify_id_token)):
    """
    POST /triage
    Main stateful symptom-intake triage loop.
    Steps:
      1. Fetch current session state from Firestore (created during Auth session on frontend).
      2. Deterministic red flag safety check.
      3. Gemini-driven slot-filling / extraction / follow-up loop.
      4. Specialist backstop table verification on completion.
      5. Persist updated session state back to Firestore.
    """
    logger.info(f"Received triage request. Session: {request.session_id}, User: {uid}, Turn: {request.turn_count}")
    
    try:
        # 1. Load session state from Firestore
        session_doc = get_session(request.session_id)
        if session_doc:
            session_state = SessionState(**session_doc.get("slot_fields", {}))
            logger.info(f"Loaded existing session state from Firestore for ID {request.session_id}")
        else:
            session_state = SessionState()
            logger.info(f"No previous state found. Initializing blank session state for ID {request.session_id}")

        # If a non-English language is specified, translate the transcript to English first
        if request.language != "en":
            original_transcript = request.transcript
            logger.info(f"Translating transcript from {request.language} to English...")
            request.transcript = translate_text(request.transcript, target_language="en")
            logger.info(f"Translated transcript: '{request.transcript}'")
        else:
            original_transcript = request.transcript

        # 2. Deterministic Red Flag check (raw transcript + current severity in loaded session_state)
        emergency_message = check_red_flags(request.transcript, session_state.severity)
        if emergency_message:
            logger.info("Red flag triggered! Saving emergency status and directing to emergency response.")
            session_state.red_flags_present = ["Triggered by emergency patterns"]
            
            # Persist the emergency status to Firestore
            update_session(
                session_id=request.session_id,
                uid=uid,
                slot_fields=session_state.dict(),
                turn_count=request.turn_count,
                triage_result={
                    "urgency_level": "emergency",
                    "specialist_type": "general_physician",
                    "confidence": "high",
                    "red_flags_triggered": ["Triggered by emergency patterns"],
                    "reasoning_summary": "Emergency red flags triggered deterministically outside of LLM."
                }
            )
            return EmergencyResponse(
                status="emergency",
                message=emergency_message
            )
            
        # 3. Process conversation with Gemini Flash via Vertex AI
        gemini_data = call_gemini_triage(request.transcript, session_state, request.turn_count, request.max_turns, request.language)
        
        # 4. Handle completion vs follow-up
        status = gemini_data.get("status", "follow_up")
        updated_state_dict = gemini_data.get("updated_session_state", {})
        
        # Post-Gemini Extraction Clinical Safety Guard:
        # If Gemini extracted a high severity (>= 9) or any symptom triggers a red flag, short-circuit immediately.
        extracted_severity = updated_state_dict.get("severity")
        emergency_message = check_red_flags(request.transcript, extracted_severity)
        if emergency_message:
            logger.info("Red flag or critical severity (>= 9) detected in post-Gemini extracted state! Short-circuiting to emergency response.")
            updated_state_dict["red_flags_present"] = ["Triggered by emergency or high severity"]
            
            # Persist the emergency status to Firestore
            update_session(
                session_id=request.session_id,
                uid=uid,
                slot_fields=updated_state_dict,
                turn_count=request.turn_count,
                triage_result={
                    "urgency_level": "emergency",
                    "specialist_type": "general_physician",
                    "confidence": "high",
                    "red_flags_triggered": ["Triggered by emergency or high severity"],
                    "reasoning_summary": f"Emergency short-circuit triggered post-LLM extraction due to high severity ({extracted_severity}/10) or red-flag symptom matches."
                }
            )
            return EmergencyResponse(
                status="emergency",
                message=emergency_message
            )
            
        if status == "triage_complete":
            # Extract triage results and apply specialist backstop check
            triage_result_dict = gemini_data.get("triage_result", {})
            model_specialist = triage_result_dict.get("specialist_type", "general_physician")
            
            # Combine chief complaint and associated symptoms to feed into the keyword backstop
            chief_complaint = updated_state_dict.get("chief_complaint") or ""
            associated_symptoms = " ".join(updated_state_dict.get("associated_symptoms", []))
            symptoms_text = f"{chief_complaint} {associated_symptoms}"
            
            # Apply Specialist Backstop
            final_specialist = apply_specialist_backstop(symptoms_text, model_specialist)
            triage_result_dict["specialist_type"] = final_specialist
            
            logger.info(f"Triage complete. Final specialist: {final_specialist}, Urgency: {triage_result_dict.get('urgency_level')}")
            
            # If a non-English language was used, translate the reasoning summary back
            if request.language != "en":
                if "reasoning_summary" in triage_result_dict:
                    triage_result_dict["reasoning_summary"] = translate_text(triage_result_dict["reasoning_summary"], request.language)

            # Persist complete state to Firestore
            update_session(
                session_id=request.session_id,
                uid=uid,
                slot_fields=updated_state_dict,
                turn_count=request.turn_count,
                triage_result=triage_result_dict
            )

            return TriageCompleteResponse(
                status="triage_complete",
                updated_session_state=updated_state_dict,
                triage_result=triage_result_dict
            )
            
        else:
            # Continue the follow-up flow
            follow_up_question = gemini_data.get("follow_up_question") or gemini_data.get("response", {}).get("follow_up_question", "Could you provide more details about how you are feeling?")
            if request.language != "en":
                follow_up_question = translate_text(follow_up_question, request.language)
            
            logger.info(f"Triage follow-up generated: '{follow_up_question}'")
            
            # Persist updated session state to Firestore
            update_session(
                session_id=request.session_id,
                uid=uid,
                slot_fields=updated_state_dict,
                turn_count=request.turn_count,
                triage_result=None
            )
            
            return FollowUpResponse(
                status="follow_up",
                updated_session_state=updated_state_dict,
                follow_up_question=follow_up_question
            )
            
    except Exception as e:
        logger.error(f"Error processing triage request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Simple endpoint to confirm the service is running and healthy."""
    return {"status": "healthy", "service": "carepathai-backend"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = "en"):
    """
    POST /transcribe
    Upload an audio file (WebM, WAV, OGG, MP3, etc.) recorded via browser mic.
    Returns the transcribed text with pre-selected primary and fallback languages.
    """
    logger.info(f"Received audio file for transcription: '{file.filename}', content_type: '{file.content_type}', selected language: '{language}'")
    
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded audio file is empty.")
            
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=content)
        
        # Configure Speech Adaptation (Phrase Boosting) with a medical/anatomical vocabulary
        # to bias the STT model to transcribe words like "knee" instead of "Ni" or "to" instead of "Tu".
        phrases = [
            "knee", "joint", "shoulder", "back pain", "elbow", "bone", "fracture", "sprain", "arthritis",
            "skin", "rash", "itching", "acne", "pimple", "bump", "tender", "tender to touch",
            "cough", "breathlessness", "asthma", "chest pain", "heart", "stomach", "abdominal",
            "nausea", "vomiting", "diarrhea", "acidity", "ear", "nose", "throat", "it is", "to touch"
        ]
        
        # Add common symptom-related words depending on pre-selected language to improve accent-specific accuracy
        if language == "hi":
            phrases.extend([
                "बुखार", "दर्द", "सिरदर्द", "खांसी", "जुकाम", "उल्टी", "दस्त", "जलन", "कमजोरी", "थकान",
                "अब", "दिन", "हफ्ते", "महीने", "से", "ज्यादा", "कम", "ठीक", "खराब"
            ])
        else:
            phrases.extend([
                "now", "fever", "pain", "severe", "days", "weeks", "months", "since", "headache", "cold", "flu",
                "coughing", "sneezing", "congestion", "blockage", "runny nose", "sore throat", "burning sensation",
                "burning", "sharp pain", "dull pain", "constantly", "on and off", "worse", "better", "improving"
            ])

        speech_contexts = [
            speech.SpeechContext(
                phrases=phrases,
                boost=15.0  # High boost factor to ensure Google favors these phrases phonetically
            )
        ]
        
        # Boost single-digit and multi-digit numbers to help with short utterances (like "seven")
        number_phrases_en = [
            "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"
        ]
        number_phrases_hi = [
            "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ", "दस",
            "१", "२", "३", "४", "५", "६", "७", "८", "९", "१०"
        ]
        number_phrases = number_phrases_hi if language == "hi" else number_phrases_en
        
        speech_contexts.append(
            speech.SpeechContext(
                phrases=number_phrases,
                boost=20.0  # Very high boost factor to prioritize single-digit numbers in short clips
            )
        )
        
        # Configure primary and alternative languages based on pre-selection
        primary_lang = "hi-IN" if language == "hi" else "en-IN"
        
        # We use ENCODING_UNSPECIFIED so Google Speech-to-Text auto-detects WAV, WebM, Ogg, MP3, etc.
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
            language_code=primary_lang,
            audio_channel_count=2,
            enable_separate_recognition_per_channel=True,
            use_enhanced=True,  # Set to true to use enhanced models for higher accuracy (best practice)
            enable_automatic_punctuation=True,
            speech_contexts=speech_contexts,  # Add Speech Contexts!
        )
        
        logger.info("Calling Google Cloud Speech-to-Text API...")
        response = client.recognize(config=config, audio=audio)



        
        # Extract transcribed text
        # The API is now configured to handle stereo and will return a result for each channel.
        # We only need the transcription from the first channel.
        if response.results:
            transcript = response.results[0].alternatives[0].transcript
        else:
            transcript = ""
        logger.info(f"Transcription complete. Transcribed text: '{transcript}'")
        
        return {"transcript": transcript}
        
    except Exception as e:
        logger.error(f"Error during transcription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/translate-results", response_model=TriageCompleteResponse)
async def translate_results(session_id: str, language: str, uid: str = Depends(verify_id_token)):
    logger.info(f"Received request to translate results for session {session_id} to {language}")
    try:
        session_doc = get_session(session_id)
        if not session_doc:
            raise HTTPException(status_code=404, detail="Session not found.")

        triage_result = dict(session_doc.get("triage_result", {}))
        session_state = dict(session_doc.get("slot_fields", {}))

        # Collect translation jobs for concurrent parallel execution
        jobs = []

        # 1. Collect session_state tasks
        for key, value in session_state.items():
            if isinstance(value, str) and value.strip():
                jobs.append(("session_state_str", key, async_translate_text(value, language)))
            elif isinstance(value, list) and value:
                for idx, item in enumerate(value):
                    if isinstance(item, str) and item.strip():
                        jobs.append(("session_state_list", (key, idx), async_translate_text(item, language)))

        # 2. Collect triage_result tasks
        for key in ["reasoning_summary", "chief_complaint", "clinical_reasoning"]:
            if key in triage_result and isinstance(triage_result[key], str) and triage_result[key].strip():
                jobs.append(("triage_result", key, async_translate_text(triage_result[key], language)))

        if jobs:
            # Execute all translation jobs concurrently in parallel
            results = await asyncio.gather(*[j[2] for j in jobs], return_exceptions=True)

            for (target_type, target_key, _), translated_val in zip(jobs, results):
                if isinstance(translated_val, Exception):
                    logger.error(f"Translation job exception for {target_type} {target_key}: {translated_val}")
                    continue

                if target_type == "session_state_str":
                    session_state[target_key] = translated_val
                elif target_type == "session_state_list":
                    s_key, s_idx = target_key
                    session_state[s_key][s_idx] = translated_val
                elif target_type == "triage_result":
                    triage_result[target_key] = translated_val

        return TriageCompleteResponse(
            status="triage_complete",
            updated_session_state=session_state,
            triage_result=triage_result
        )

    except Exception as e:
        logger.error(f"Error translating results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/doctors", response_model=DoctorSearchResponse)
async def get_doctors(request: DoctorSearchRequest, uid: str = Depends(verify_id_token)):
    """
    POST /doctors
    Takes location, radius, and specialist type. Requiring dynamic anonymous authorization header.
    Returns a ranked list of top 5-8 doctors, sorted by rating (desc) then distance (asc).
    Uses live Google Places Nearby Search, falling back to a realistic local mock database if needed.
    """
    logger.info(f"Received doctor search request. Specialist: {request.specialist_type}, Location: ({request.lat}, {request.lng}), Radius: {request.radius_km} km, User: {uid}")
    try:
        doctors = search_nearby_doctors(request)
        return DoctorSearchResponse(status="success", doctors=doctors)
    except Exception as e:
        logger.error(f"Error searching doctors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



