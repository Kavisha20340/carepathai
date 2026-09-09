from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Union, Optional
import logging
import asyncio

# Import the new and existing models and logic
from backend.models import (
    TriageRequest, FollowUpResponse, TriageCompleteResponse, 
    EmergencyResponse, DoctorSearchRequest, DoctorSearchResponse, TriageResult, SessionState,
    TranslateResultsResponse, SaveReportTraceRequest
)
from backend.reasoning_logic import run_clinical_reasoning_turn
from backend.translation_logic import (
    translate_text, transcribe_audio, denoise_transcript_with_context, async_translate_text
)
from backend.places_logic import search_nearby_doctors
from backend.auth_logic import verify_id_token
from backend.firestore_logic import get_session, update_session, save_report_trace

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CarepathAI Triage API - v2.0 (MedGemma)", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_SPECIALISTS = {
    'general_physician', 'orthopedic', 'dermatologist', 'pulmonologist',
    'cardiologist', 'gastroenterologist', 'ent', 'gynecologist',
    'pediatrician', 'ophthalmologist', 'psychiatrist', 'neurologist',
    'urologist', 'dentist', 'endocrinologist', 'nephrologist',
    'oncologist', 'rheumatologist', 'general_surgeon'
}

def _sanitize_specialist_type(raw_specialty: Union[str, None]) -> str:
    if not raw_specialty or not isinstance(raw_specialty, str):
        return 'general_physician'
    formatted = raw_specialty.strip().lower().replace('-', '_').replace(' ', '_')
    if formatted in ALLOWED_SPECIALISTS:
        return formatted
    
    # Flexible keyword/synonym alias mapping
    if any(kw in formatted for kw in ['derma', 'skin']):
        return 'dermatologist'
    if any(kw in formatted for kw in ['ortho', 'bone', 'joint']):
        return 'orthopedic'
    if any(kw in formatted for kw in ['cardio', 'heart']):
        return 'cardiologist'
    if any(kw in formatted for kw in ['pulm', 'lung', 'respirat']):
        return 'pulmonologist'
    if any(kw in formatted for kw in ['gastro', 'stomach', 'digest']):
        return 'gastroenterologist'
    if any(kw in formatted for kw in ['ear', 'nose', 'throat', 'ent']):
        return 'ent'
    if any(kw in formatted for kw in ['gyno', 'gynec', 'women']):
        return 'gynecologist'
    if any(kw in formatted for kw in ['pedia', 'child']):
        return 'pediatrician'
    if any(kw in formatted for kw in ['ophthal', 'eye', 'vision']):
        return 'ophthalmologist'
    if any(kw in formatted for kw in ['psych', 'mental']):
        return 'psychiatrist'
    if any(kw in formatted for kw in ['neuro', 'nerve', 'brain']):
        return 'neurologist'
    if any(kw in formatted for kw in ['uro', 'urinary', 'bladder']):
        return 'urologist'
    if any(kw in formatted for kw in ['dent', 'tooth', 'teeth', 'oral']):
        return 'dentist'
    if any(kw in formatted for kw in ['endo', 'diabet', 'thyroid']):
        return 'endocrinologist'
    if any(kw in formatted for kw in ['nephro', 'kidney']):
        return 'nephrologist'
    if any(kw in formatted for kw in ['onco', 'cancer', 'tumor']):
        return 'oncologist'
    if any(kw in formatted for kw in ['rheuma', 'arthrit']):
        return 'rheumatologist'
    if any(kw in formatted for kw in ['surg', 'operat']):
        return 'general_surgeon'
    if any(kw in formatted for kw in ['physician', 'doctor', 'gp', 'general', 'primary']):
        return 'general_physician'
        
    return 'general_physician'

def _map_confidence_to_literal(score) -> str:
    if isinstance(score, str):
        s = score.lower().strip()
        if s in ['high', 'moderate', 'low']:
            return s
        if s == 'medium':
            return 'moderate'
        try:
            score = float(s)
        except ValueError:
            return 'low'
    if isinstance(score, (int, float)):
        if score >= 0.9:
            return 'high'
        elif score >= 0.7:
            return 'moderate'
        else:
            return 'low'
    return 'low'


async def translate_triage_data(
    triage_result: TriageResult, 
    session_state: SessionState, 
    target_language: str
) -> tuple[TriageResult, SessionState]:
    """
    Translates triage results and session state fields concurrently to the target language.
    If target_language is 'en', returns original English models directly.
    """
    if target_language == 'en':
        return triage_result, session_state

    to_translate = {}

    # A. Dynamic reasoning summary
    if triage_result.reasoning_summary:
        to_translate['reasoning_summary'] = triage_result.reasoning_summary

    # B. SessionState fields
    if session_state.chief_complaint:
        to_translate['chief_complaint'] = session_state.chief_complaint
    if session_state.body_location:
        to_translate['body_location'] = session_state.body_location
    if session_state.onset:
        to_translate['onset'] = session_state.onset
    if session_state.duration:
        to_translate['duration'] = session_state.duration
    if session_state.severity and isinstance(session_state.severity, str):
        to_translate['severity'] = session_state.severity
    if session_state.aggravating_factors:
        to_translate['aggravating_factors'] = session_state.aggravating_factors
    if session_state.relevant_history:
        to_translate['relevant_history'] = session_state.relevant_history

    # C. Lists
    for i, symptom in enumerate(session_state.associated_symptoms):
        if symptom and isinstance(symptom, str):
            to_translate[f'symptom_{i}'] = symptom

    for i, flag in enumerate(session_state.red_flags_present):
        if flag and isinstance(flag, str):
            to_translate[f'red_flag_present_{i}'] = flag

    for i, flag in enumerate(triage_result.red_flags_triggered):
        if flag and isinstance(flag, str):
            to_translate[f'red_flag_triggered_{i}'] = flag

    if not to_translate:
        return triage_result, session_state

    # Translate concurrently
    keys = list(to_translate.keys())
    original_texts = [to_translate[k] for k in keys]

    logger.info(f"Translating {len(original_texts)} fields concurrently to '{target_language}'...")
    translated_texts = await asyncio.gather(*[
        async_translate_text(text, target_language=target_language)
        for text in original_texts
    ])
    translated_map = dict(zip(keys, translated_texts))

    # Reassemble objects
    if 'reasoning_summary' in translated_map:
        triage_result.reasoning_summary = translated_map['reasoning_summary']
    if 'chief_complaint' in translated_map:
        session_state.chief_complaint = translated_map['chief_complaint']
    if 'body_location' in translated_map:
        session_state.body_location = translated_map['body_location']
    if 'onset' in translated_map:
        session_state.onset = translated_map['onset']
    if 'duration' in translated_map:
        session_state.duration = translated_map['duration']
    if 'severity' in translated_map:
        session_state.severity = translated_map['severity']
    if 'aggravating_factors' in translated_map:
        session_state.aggravating_factors = translated_map['aggravating_factors']
    if 'relevant_history' in translated_map:
        session_state.relevant_history = translated_map['relevant_history']

    translated_symptoms = []
    for i in range(len(session_state.associated_symptoms)):
        key = f'symptom_{i}'
        translated_symptoms.append(translated_map.get(key, session_state.associated_symptoms[i]))
    session_state.associated_symptoms = translated_symptoms

    translated_red_flags_present = []
    for i in range(len(session_state.red_flags_present)):
        key = f'red_flag_present_{i}'
        translated_red_flags_present.append(translated_map.get(key, session_state.red_flags_present[i]))
    session_state.red_flags_present = translated_red_flags_present

    translated_red_flags_triggered = []
    for i in range(len(triage_result.red_flags_triggered)):
        key = f'red_flag_triggered_{i}'
        translated_red_flags_triggered.append(translated_map.get(key, triage_result.red_flags_triggered[i]))
    triage_result.red_flags_triggered = translated_red_flags_triggered

    return triage_result, session_state


@app.post("/triage", response_model=Union[FollowUpResponse, TriageCompleteResponse, EmergencyResponse])
async def triage(request: TriageRequest, background_tasks: BackgroundTasks, uid: str = Depends(verify_id_token)):
    """
    Main stateful symptom-intake triage loop, powered by the MedGemma Clinical Reasoning Engine.
    Orchestrates the "Translate -> Reason -> Translate" workflow.
    """
    logger.info(f"===> [APP REQUEST: /triage] Session: {request.session_id} | Turn: {request.turn_count} | Lang: {request.language} | Modality: {request.input_modality} | Transcript: '{request.transcript}'")

    if not request.transcript or not request.transcript.strip():
        logger.warning(f"Empty transcript received in /triage for session {request.session_id}")
        raise HTTPException(status_code=400, detail="Transcript text cannot be empty.")

    try:
        # 1. Load session state from Firestore
        session_doc = get_session(request.session_id)
        session_state = session_doc.get("session_state", {}) if session_doc else {}
        conversation_history = session_doc.get("conversation_history", []) if session_doc else []

        # 2. Denoise STT transcript using conversation context via Gemini Flash
        clean_transcript = denoise_transcript_with_context(
            raw_transcript=request.transcript,
            conversation_history=conversation_history,
            language=request.language
        )

        # 3. TRANSLATE TO ENGLISH (if necessary)
        transcript_for_ai = clean_transcript
        if request.language == 'hi':
            transcript_for_ai = translate_text(clean_transcript, "en")

        # 3. REASON IN ENGLISH (Call the reasoning engine with current conversation context)
        medgemma_response = run_clinical_reasoning_turn(
            conversation_history=conversation_history,
            user_transcript=transcript_for_ai,
            input_modality=request.input_modality,
            turn_count=request.turn_count,
            max_turns=request.max_turns
        )

        # Extract AI question and check against PREVIOUS turns before appending current turn
        previous_ai_questions = [
            line.replace("AI:", "").strip().lower() 
            for line in conversation_history if line.startswith("AI:")
        ]
        
        # 4. Append history cleanly AFTER reasoning turn
        conversation_history.append(f"User: {transcript_for_ai}")
        ai_question = medgemma_response.get('conversation_status', {}).get('next_question_to_user')
        if ai_question:
            conversation_history.append(f"AI: {ai_question}")

        # Update session_state with any fields extracted by the AI
        summary_from_ai = medgemma_response.get("final_summary", {})
        if summary_from_ai:
            session_state_fields = SessionState.model_fields.keys()
            update_data = {}
            for key in summary_from_ai:
                if key in session_state_fields and summary_from_ai.get(key) is not None:
                    val = summary_from_ai[key]
                    # Sanitize list/string mismatches from LLM output
                    if key in ['associated_symptoms', 'red_flags_present']:
                        if isinstance(val, str):
                            val = [val.strip()] if val.strip() else []
                        elif not isinstance(val, list):
                            val = []
                    else:
                        if isinstance(val, list):
                            val = ", ".join(str(x) for x in val if x) if val else None
                    if val is not None:
                        update_data[key] = val

            if update_data:
                session_state.update(update_data)
                logger.info(f"Updated session_state with: {update_data}")

        # Tiered urgency logic
        urgency_level = medgemma_response.get('urgency', {}).get('level', '').replace('-', '_').lower()
        urgency_justification = medgemma_response.get('urgency', {}).get('justification', '')
        urgency_warning_message = None

        # TIER 1: EMERGENCY
        if urgency_level == 'emergency':
            logger.warning(f"Emergency identified: {urgency_justification}")
            message = urgency_justification
            if request.language == 'hi':
                message = translate_text(message, 'hi')
            
            background_tasks.add_task(
                update_session,
                session_id=request.session_id, uid=uid, session_state=session_state,
                turn_count=request.turn_count, conversation_history=conversation_history,
                triage_result=medgemma_response
            )
            response_obj = EmergencyResponse(status='emergency', message=message)
            logger.info(f"<=== [APP RESPONSE: /triage] Emergency Status: {response_obj}")
            return response_obj
        
        # TIER 2: URGENT
        elif urgency_level == 'urgent':
            logger.info(f"Urgent condition identified: {urgency_justification}")
            urgency_warning_message = urgency_justification
            if request.language == 'hi':
                urgency_warning_message = translate_text(urgency_warning_message, 'hi')

        # 5. Decide whether to follow-up or complete the triage
        is_complete = medgemma_response.get('conversation_status', {}).get('is_complete', False)
        
        # Check if the AI's question is a duplicate of a previously asked question in history
        next_q = medgemma_response.get('conversation_status', {}).get('next_question_to_user')
        if next_q and next_q.strip().lower() in previous_ai_questions:
            logger.warning(f"MedGemma attempted to repeat a previously asked question ('{next_q}'). Forcing triage completion.")
            is_complete = True

        # HARD SAFETY GUARDRAIL: Force completion if turn_count >= max_turns
        if request.turn_count >= request.max_turns:
            logger.info(f"Max turns ({request.max_turns}) reached (Current turn: {request.turn_count}). Forcing triage completion.")
            is_complete = True

        if not is_complete:
            # Follow-up required
            question = medgemma_response.get('conversation_status', {}).get('next_question_to_user') or "Could you describe your symptoms further?"
            if request.language == 'hi':
                question = translate_text(question, 'hi')
            
            background_tasks.add_task(
                update_session,
                session_id=request.session_id, uid=uid, session_state=session_state,
                turn_count=request.turn_count, conversation_history=conversation_history
            )
            response_obj = FollowUpResponse(
                status='follow_up',
                updated_session_state=session_state,
                follow_up_question=question,
                urgency_warning=urgency_warning_message,
                denoised_transcript=clean_transcript
            )
            logger.info(f"<=== [APP RESPONSE: /triage] Follow-up question: '{question}' | Urgency Warning: '{urgency_warning_message}'")
            return response_obj
        else:
            # Triage is complete
            logger.info("Triage complete. Generating final summary.")
            summary = medgemma_response.get('final_summary', {}) or {}
            raw_specialty = summary.get('specialty_recommendation')
            clinical_reasoning = summary.get('clinical_reasoning') or 'Evaluation complete.'
            
            if not raw_specialty and session_state.get('chief_complaint'):
                raw_specialty = 'general_physician'
            if not clinical_reasoning or clinical_reasoning == 'Evaluation complete.':
                if session_state.get('chief_complaint'):
                    clinical_reasoning = f"Evaluation complete for reported complaint: {session_state.get('chief_complaint')}."

            triage_result = TriageResult(
                urgency_level=urgency_level if urgency_level in ['emergency', 'urgent', 'routine', 'self_care'] else 'routine',
                specialist_type=_sanitize_specialist_type(raw_specialty),
                confidence=_map_confidence_to_literal(medgemma_response.get('conversation_status', {}).get('confidence_score')),
                reasoning_summary=clinical_reasoning,
                red_flags_triggered=[]
            )
            
            # Reconstruct English structures
            session_state_model = SessionState(**session_state)

            # Save clean English structures to Firestore background task
            background_tasks.add_task(
                update_session,
                session_id=request.session_id, uid=uid, session_state=session_state,
                turn_count=request.turn_count, conversation_history=conversation_history,
                triage_result=medgemma_response
            )

            # Translate response data to requested language
            triage_result, session_state_model = await translate_triage_data(
                triage_result, session_state_model, request.language or 'en'
            )
            
            response_obj = TriageCompleteResponse(
                status='triage_complete',
                updated_session_state=session_state_model,
                triage_result=triage_result,
                urgency_warning=urgency_warning_message,
                denoised_transcript=clean_transcript
            )
            logger.info(f"<=== [APP RESPONSE: /triage] Triage Complete Result: Urgency={triage_result.urgency_level} | Specialist={triage_result.specialist_type} | Confidence={triage_result.confidence}")
            return response_obj

    except HTTPException as http_ex:
        # Re-raise explicit HTTP exceptions (e.g., 400, 503) without converting to 500
        raise http_ex
    except Exception as e:
        logger.error(f"An unexpected error occurred in /triage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")


@app.post("/doctors", response_model=DoctorSearchResponse)
def get_doctors(request: DoctorSearchRequest, uid: str = Depends(verify_id_token)):
    """
    Searches for doctors based on specialty and location.
    """
    logger.info(f"===> [APP REQUEST: /doctors] Specialty: '{request.specialist_type}' | GPS: ({request.lat}, {request.lng}) | Radius: {request.radius_km} km | Ratings: [{request.min_rating}-{request.max_rating}]")
    try:
        doctors = search_nearby_doctors(request)
        response_obj = DoctorSearchResponse(status="success", doctors=doctors)
        logger.info(f"<=== [APP RESPONSE: /doctors] Returned {len(doctors)} doctors for specialty: '{request.specialist_type}'")
        return response_obj
    except Exception as e:
        logger.error(f"Error in /doctors endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search for doctors.")


@app.post("/transcribe")
def transcribe(file: UploadFile = File(...), language: str = "en", session_id: Optional[str] = None):
    """
    Transcribes audio to text using Google Cloud Speech-to-Text and immediately
    denoises it with context via Gemini Flash to provide instant UI autocorrection.
    """
    logger.info(f"===> [APP REQUEST: /transcribe] File: '{file.filename}' | Language: '{language}' | Session ID: '{session_id}'")
    try:
        # 1. Google Speech-to-Text
        result = transcribe_audio(file.file, language)
        raw_transcript = result.get('transcript', '')

        # 2. Context-Aware Denoising via Gemini Flash (Completed in <200ms)
        if raw_transcript and session_id:
            session_doc = get_session(session_id)
            conversation_history = session_doc.get("conversation_history", []) if session_doc else []
            clean_transcript = denoise_transcript_with_context(
                raw_transcript=raw_transcript,
                conversation_history=conversation_history,
                language=language
            )
            result['transcript'] = clean_transcript

        logger.info(f"<=== [APP RESPONSE: /transcribe] Transcribed & Denoised Text: '{result.get('transcript', '')}'")
        return result
    except Exception as e:
        logger.error(f"Error during transcription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during transcription.")
    


@app.post("/translate-results", response_model=TranslateResultsResponse)
async def translate_results(
    session_id: str,
    language: str,
    uid: str = Depends(verify_id_token)
):
    """
    Translates the triage results and updated session state from English to the target language (e.g. Hindi),
    with parallel async gathering and Firestore caching.
    """
    logger.info(f"===> [APP REQUEST: /translate-results] Session: {session_id} | Target Lang: {language}")

    # 1. Fetch session from Firestore
    session_doc = get_session(session_id)
    if not session_doc:
        logger.warning(f"Session {session_id} not found in Firestore for translation.")
        raise HTTPException(status_code=404, detail="Session not found.")

    # 2. Extract and reconstruct original English models
    raw_session_state = session_doc.get("session_state", {})
    medgemma_response = session_doc.get("triage_result") or {}

    # Extract the necessary values
    summary = medgemma_response.get('final_summary', {}) or {}
    raw_specialty = summary.get('specialty_recommendation')
    clinical_reasoning = summary.get('clinical_reasoning') or 'Evaluation complete.'
    urgency_level = medgemma_response.get('urgency', {}).get('level', '').lower()

    # Reconstruct English structures
    session_state = SessionState(**raw_session_state)
    triage_result = TriageResult(
        urgency_level=urgency_level if urgency_level in ['emergency', 'urgent', 'routine', 'self_care'] else 'routine',
        specialist_type=_sanitize_specialist_type(raw_specialty),
        confidence=_map_confidence_to_literal(medgemma_response.get('conversation_status', {}).get('confidence_score')),
        reasoning_summary=clinical_reasoning,
        red_flags_triggered=[]
    )

    # 3. Translate response data to target language concurrently using helper
    triage_result, session_state = await translate_triage_data(
        triage_result, session_state, language
    )

    logger.info(f"<=== [APP RESPONSE: /translate-results] Successfully translated results for session {session_id}")
    return TranslateResultsResponse(
        triage_result=triage_result,
        updated_session_state=session_state
    )



@app.post("/save-report-trace")
def save_report_trace_endpoint(request: SaveReportTraceRequest, uid: str = Depends(verify_id_token)):
    """
    Saves a report download trace (textual content, timestamp, language) to the session document in Firestore.
    """
    logger.info(f"===> [APP REQUEST: /save-report-trace] Session: {request.session_id} | Lang: {request.language}")
    success = save_report_trace(request.session_id, request.language, request.report_text)
    if not success:
        logger.warning(f"Failed to save report trace for session {request.session_id}")
    return {"status": "success" if success else "failed"}

