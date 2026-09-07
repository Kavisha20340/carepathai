from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Union, Optional
import logging

# Import the new and existing models and logic
from backend.models import (
    TriageRequest, FollowUpResponse, TriageCompleteResponse, 
    EmergencyResponse, DoctorSearchRequest, DoctorSearchResponse, TriageResult, SessionState
)
from backend.reasoning_logic import run_clinical_reasoning_turn
from backend.translation_logic import translate_text, transcribe_audio, denoise_transcript_with_context
from backend.places_logic import search_nearby_doctors
from backend.auth_logic import verify_id_token
from backend.firestore_logic import get_session, update_session

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
    'pediatrician', 'ophthalmologist', 'psychiatrist'
}

def _sanitize_specialist_type(raw_specialty: Union[str, None]) -> str:
    if not raw_specialty or not isinstance(raw_specialty, str):
        return 'general_physician'
    formatted = raw_specialty.strip().lower().replace(' ', '_')
    if formatted in ALLOWED_SPECIALISTS:
        return formatted
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

@app.post("/triage", response_model=Union[FollowUpResponse, TriageCompleteResponse, EmergencyResponse])
def triage(request: TriageRequest, background_tasks: BackgroundTasks, uid: str = Depends(verify_id_token)):
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

        # 4. Append history cleanly AFTER reasoning turn
        conversation_history.append(f"User: {transcript_for_ai}")
        ai_question = medgemma_response.get('conversation_status', {}).get('next_question_to_user')
        if ai_question:
            conversation_history.append(f"AI: {ai_question}")

        # Update session_state with any fields extracted by the AI
        summary_from_ai = medgemma_response.get("final_summary", {})
        if summary_from_ai:
            session_state_fields = SessionState.model_fields.keys()
            update_data = {
                key: summary_from_ai[key] for key in summary_from_ai
                if key in session_state_fields and summary_from_ai.get(key) is not None
            }
            if update_data:
                session_state.update(update_data)
                logger.info(f"Updated session_state with: {update_data}")

        # Tiered urgency logic
        urgency_level = medgemma_response.get('urgency', {}).get('level', '').lower()
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
        if not medgemma_response.get('conversation_status', {}).get('is_complete'):
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
            
            triage_result = TriageResult(
                urgency_level=urgency_level if urgency_level in ['emergency', 'urgent', 'routine', 'self_care'] else 'routine',
                specialist_type=_sanitize_specialist_type(raw_specialty),
                confidence=_map_confidence_to_literal(medgemma_response.get('conversation_status', {}).get('confidence_score')),
                reasoning_summary=clinical_reasoning,
                red_flags_triggered=[]
            )
            
            if request.language == 'hi':
                if summary.get('chief_complaint'):
                    summary['chief_complaint'] = translate_text(summary.get('chief_complaint', ''), 'hi')
                if triage_result.reasoning_summary:
                    triage_result.reasoning_summary = translate_text(triage_result.reasoning_summary, 'hi')

            background_tasks.add_task(
                update_session,
                session_id=request.session_id, uid=uid, session_state=session_state,
                turn_count=request.turn_count, conversation_history=conversation_history,
                triage_result=medgemma_response
            )
            
            response_obj = TriageCompleteResponse(
                status='triage_complete',
                updated_session_state=session_state,
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
    