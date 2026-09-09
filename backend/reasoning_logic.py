
import logging
from typing import List, Dict
from backend.medgemma_client import query_medgemma
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def construct_prompt(
    conversation_history: List[str], 
    user_transcript: str, 
    input_modality: str, 
    turn_count: int, 
    max_turns: int
) -> str:
    """Constructs a dense, compressed prompt for the MedGemma clinical reasoning engine."""

    # Compact JSON schema
    json_schema = '''{
        "urgency": {
            "level": "One of: 'Emergency', 'Urgent', 'Routine', 'Self-care'",
            "justification": "Brief clinical reasoning. (10 words max)"
        },
        "conversation_status": {
            "is_complete": "boolean, true if triage is over or symptoms clear, false if follow-up needed.",
            "next_question_to_user": "Single critical follow-up question. MUST be null if is_complete is true.",
            "confidence_score": "Float 0.0-1.0 representing confidence."
        },
        "final_summary": {
            "chief_complaint": "Short summary of primary issue. MUST be null if is_complete is false.",
            "body_location": "Affected body part or null if unknown.",
            "onset": "When symptoms started or null if unknown.",
            "duration": "Symptom duration or null if unknown.",
            "severity": "Reported severity or null if unknown.",
            "associated_symptoms": ["List of other mentioned symptoms"],
            "aggravating_factors": "Triggers or factors that worsen symptoms, or null if unknown.",
            "specialty_recommendation": "One of: 'General Physician', 'Orthopedic', 'Dermatologist', 'Pulmonologist', 'Cardiologist', 'Gastroenterologist', 'ENT Specialist', 'Gynecologist', 'Pediatrician', 'Ophthalmologist', 'Psychiatrist', 'Neurologist', 'Urologist', 'Dentist', 'Endocrinologist', 'Nephrologist', 'Oncologist', 'Rheumatologist', 'General Surgeon'. Identify appropriate specialist REGARDLESS of urgency level. MUST default to 'General Physician' if non-specific or unsure. MUST be null if is_complete is false.",
            "clinical_reasoning": "Concise reasoning for recommendation (50 words max). MUST be null if is_complete is false."
        }
    }'''

    history_str = "\n".join(conversation_history) if conversation_history else "None"

    prompt = f"""You are MedGemma, a fast Triage Navigator. Turn {turn_count}/{max_turns}.
DIRECTIVES:
1. Output ONLY valid JSON matching schema.
2. Be extremely concise in justifications.
3. If symptoms & specialty are clear or turn_count == max_turns, set is_complete=true.
4. If is_complete is false, next_question_to_user MUST be a non-null question and final_summary fields MUST be null.
5. MANDATORY WHEN COMPLETE: When is_complete is true, urgency.level MUST NOT be null, and specialty_recommendation MUST NOT be null. Determine specialty_recommendation purely by identifying the appropriate clinical specialist for the reported symptoms, REGARDLESS of the urgency level (e.g., recommend 'Dermatologist' for a skin rash even if urgency is 'Self-care'). Default to 'General Physician' only if non-specific or unsure.
6. STRICT CLINICAL GROUNDING: You MUST NEVER hallucinate, infer, or add unstated symptoms (such as 'Chest Pain' or 'Shortness of breath') unless explicitly reported by the user in the conversation history or latest message.
7. CLINICAL INTAKE PRINCIPLE: Base your triage and summary strictly on the exact symptoms reported. Do NOT substitute, group, or generalize reported symptoms with different diagnostic concepts, categories, or pathologies. Use your clinical judgment to ask the single most relevant follow-up question needed to clarify the patient's condition before concluding triage.
8. NO REPETITION: Examine CONVERSATION HISTORY carefully. You MUST NEVER ask a question that has already been asked or answered in previous turns. If a question was already asked, ask a NEW relevant clinical question or set is_complete=true.
9. All text inside JSON must be in English.

CONVERSATION HISTORY:
{history_str}

LATEST USER MESSAGE:
{user_transcript}

JSON SCHEMA:
{json_schema}"""

    if input_modality == 'voice':
        transcription_warning = "NOTE: Input is from voice STT. Infer intended clinical meaning if minor phonetic artifacts exist.\n\n"
        prompt = transcription_warning + prompt

    return prompt


def run_clinical_reasoning_turn(
    conversation_history: list, 
    user_transcript: str, 
    input_modality: str, 
    turn_count: int, 
    max_turns: int
) -> Dict:
    """
    Orchestrates a single turn of the clinical reasoning process.
    1. Constructs the prompt.
    2. Queries the MedGemma model.
    3. Normalizes and returns the structured JSON response.
    """
    logger.info(f"Running clinical reasoning turn {turn_count}/{max_turns}. Input modality: {input_modality}")

    # 1. Construct the compressed prompt
    prompt = construct_prompt(
        conversation_history=conversation_history,
        user_transcript=user_transcript,
        input_modality=input_modality,
        turn_count=turn_count,
        max_turns=max_turns
    )
    
    # 2. Query MedGemma
    medgemma_response = query_medgemma(prompt)

    # 3. Validate and normalize the response
    if medgemma_response and not medgemma_response.get('error'):
        logger.info(f"Successfully received and parsed MedGemma response.")

        # Key normalization for robustness (handling aliases like status/summary)
        if 'status' in medgemma_response and 'conversation_status' not in medgemma_response:
            medgemma_response['conversation_status'] = medgemma_response.pop('status')
        
        status_block = medgemma_response.get('conversation_status', {})
        if 'next_question' in status_block and 'next_question_to_user' not in status_block:
            status_block['next_question_to_user'] = status_block.pop('next_question')
        if 'confidence' in status_block and 'confidence_score' not in status_block:
            status_block['confidence_score'] = status_block.pop('confidence')

        if 'summary' in medgemma_response and 'final_summary' not in medgemma_response:
            medgemma_response['final_summary'] = medgemma_response.pop('summary')

        return medgemma_response
    else:
        logger.error(f"MedGemma query failed or returned an error: {medgemma_response}")
        raise HTTPException(
            status_code=503, 
            detail=f"MedGemma service unavailable or returned an error: {medgemma_response.get('message', 'Unknown error')}"
        )

