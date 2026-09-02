import re
import json
import logging
from typing import Dict, Any, Optional, Tuple
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from backend.models import SessionState, TriageResult, TriageRequest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Vertex AI
try:
    vertexai.init(project="carepathai", location="us-central1")
    logger.info("Vertex AI successfully initialized in triage_logic.")
except Exception as e:
    logger.error(f"Failed to initialize Vertex AI: {e}")

# 1. Deterministic Red Flag Patterns (English + Hindi Devanagari + Hindi transliterated Roman)
RED_FLAG_PATTERNS = {
    "chest_pain_breathlessness": [
        r"(chest\s*pain|tightness\s*in\s*chest|heavy\s*chest|pressure\s*in\s*chest).*(can't\s*breathe|cannot\s*breathe|can\s*not\s*breathe|breathless|shortness\s*of\s*breath|difficulty\s*breathing|breathing\s*difficulty)",
        r"(can't\s*breathe|cannot\s*breathe|can\s*not\s*breathe|breathless|shortness\s*of\s*breath|difficulty\s*breathing|breathing\s*difficulty).*(chest\s*pain|tightness\s*in\s*chest|heavy\s*chest|pressure\s*in\s*chest)",
        r"(सीने\s*में\s*दर्द|छाती\s*में\s*दर्द|सीने\s*में\s*जकड़न|सीना\s*भारी).*(सांस\s*लेने\s*में\s*तकलीफ|सांस\s*फूलना|सांस\s*नहीं\s*आ\s*रही)",
        r"(सांस\s*लेने\s*में\s*तकलीफ|सांस\s*फूलना|सांस\s*नहीं\s*आ\s*रही).*(सीने\s*में\s*दर्द|छाती\s*में\s*दर्द|सीने\s*में\s*जकड़न|सीना\s*भारी)",
        r"(sine\s*me\s*dard|seene\s*me\s*dard|chhati\s*me\s*dard|seena\s*bhari).*(saans?\s*lene\s*me\s*taklif|saans?\s*f(u|oo)lna|saans?\s*nahi\s*aa\s*rahi|saans?\s*nahi\s*li\s*ja\s*rahi|saans?\s*nahi\s*aa\s*raha)",
        r"(saans?\s*lene\s*me\s*taklif|saans?\s*f(u|oo)lna|saans?\s*nahi\s*aa\s*rahi|saans?\s*nahi\s*li\s*ja\s*rahi|saans?\s*nahi\s*aa\s*raha).*(sine\s*me\s*dard|seene\s*me\s*dard|chhati\s*me\s*dard|seena\s*bhari)"
    ],
    "severe_bleeding": [
        r"heavy\s*bleeding|won't\s*stop\s*bleeding|bleeding\s*heavily|uncontrolled\s*bleeding",
        r"बहुत\s*खून|खून\s*बह\s*रहा\s*है|खून\s*नहीं\s*रुक\s*रहा",
        r"bohot\s*khoon|khoon\s*beh\s*raha|khoon\s*nahi\s*ruk\s*raha"
    ],
    "loss_of_consciousness": [
        r"fainted|passed\s*out|unconscious|blacked\s*out|lost\s*consciousness",
        r"बेहोश|होश\s*खो|चक्कर\s*खाकर\s*गिर",
        r"behos|behoash|chakkar\s*aakar\s*gir|hosh\s*kho"
    ],
    "stroke_signs": [
        r"face\s*drooping|slurred\s*speech|one\s*side\s*weak|paralysis|one\s*side\s*numb",
        r"चेहरा\s*लटक|आवाज\s*लड़खड़ा|एक\s*तरफ\s*कमजोरी|लकवा",
        r"chehra\s*latak|awaaz\s*ladkhada|ek\s*taraf\s*kamzori|lakwa"
    ],
    "severe_abdominal_pain": [
        r"(severe|intense|excruciating|very\s*bad).*(stomach|abdomen|belly)\s*pain",
        r"(stomach|abdomen|belly)\s*pain.*(severe|intense|excruciating|very\s*bad)",
        r"पेट\s*में\s*तेज\s*दर्द|पेट\s*में\s*बहुत\s*तेज\s*दर्द",
        r"pet\s*me\s*tez\s*dard|pet\s*me\s*bohot\s*tez\s*dard"
    ],
    "suicidal_ideation": [
        r"suicid|kill\s*myself|end\s*my\s*life|harm\s*myself|self-harm",
        r"आत्महत्या|जान\s*दे\s*दूंगा|मरना\s*चाहता",
        r"suicide|khudkhushi|jaan\s*de\s*dunga|marna\s*chahta"
    ]
}

def check_red_flags(transcript: str, severity: Optional[int]) -> Optional[str]:
    """
    Checks for red flag patterns in the transcript and severity.
    Returns the emergency message if a red flag is found, else None.
    """
    for flag_name, patterns in RED_FLAG_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, transcript, re.IGNORECASE):
                logger.info(f"Red flag triggered: {flag_name} matching pattern: {pattern}")
                return "This may be a medical emergency. Please call emergency services or go to the nearest ER immediately."
                
    if severity is not None and severity >= 9:
        logger.info(f"Red flag triggered: severity {severity} >= 9")
        return "This may be a medical emergency. Please call emergency services or go to the nearest ER immediately."
        
    return None


# 2. Specialist Backstop Lookup Table
SPECIALIST_KEYWORDS = {
    "orthopedic": [
        "joint", "knee", "back", "bone", "fracture", "sprain", "arthritis", "shoulder", "spine", "gout",
        "जोड़", "घुटने", "पीठ", "हड्डी", "कमर", "jod", "ghutna", "peeth", "haddi", "kamar"
    ],
    "dermatologist": [
        "skin", "rash", "itching", "acne", "pimple", "eczema", "psoriasis", "hives", "mole",
        "त्वचा", "खुजली", "मुहांसे", "त्वचा", "skin", "khujli", "daane", "pimples"
    ],
    "pulmonologist": [
        "cough", "breathlessness", "asthma", "wheezing", "lung", "bronchitis", "pneumonia",
        "खांसी", "दमा", "फेफड़े", "khansi", "cough", "saans"
    ],
    "cardiologist": [
        "chest pain", "heart", "palpitations", "arrhythmia", "cardiac",
        "दिल", "heart", "palpitation", "dharkan"
    ],
    "gastroenterologist": [
        "stomach", "digestion", "nausea", "vomiting", "diarrhea", "acidity", "constipation", "bloating", "gas",
        "पेट", "उल्टी", "दस्त", "vomit", "pet", "pachan", "acidity", "ulte"
    ],
    "ent": [
        "ear", "nose", "throat", "sinus", "tonsil", "hearing", "tinnitus", "hoarseness",
        "कान", "नाक", "गला", "kan", "nak", "gala"
    ],
    "ophthalmologist": [
        "eye", "vision", "blur", "cataract", "glaucoma", "blindness",
        "आंख", "drishti", "aankh", "aankhein"
    ],
    "gynecologist": [
        "period", "pregnancy", "gynaecologist", "menses", "ovary", "uterus", "vagina",
        "पीरियड", "गर्भावस्था", "mahina", "pregnancy"
    ],
    "pediatrician": [
        "baby", "child", "kid", "toddler", "pediatric", "infant",
        "बच्चा", "bacha", "shishu"
    ],
    "psychiatrist": [
        "depression", "anxiety", "panic attack", "mental health", "bipolar", "schizophrenia", "hallucination",
        "तनाव", "चिंता", "अवसाद", "chinta", "depression", "tanav"
    ]
}

def apply_specialist_backstop(symptoms_text: str, model_specialist: str) -> str:
    """
    Sanity check on the model's specialist_type.
    If a clear expected specialist is detected from keyword matches, and the model's specialist
    disagrees sharply (i.e. model_specialist is NOT the expected one AND is NOT general_physician),
    we fallback to general_physician to avoid a confidently wrong specialist.
    """
    detected_specialists = []
    for specialist, keywords in SPECIALIST_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', symptoms_text, re.IGNORECASE) or keyword in symptoms_text.lower():
                detected_specialists.append(specialist)
                break # Matched this specialist, move to next

    if detected_specialists:
        # If the model's specialist matches any detected specialist, it's perfect
        if model_specialist in detected_specialists:
            return model_specialist
        # If the model's specialist is general_physician, it's a safe default
        if model_specialist == "general_physician":
            return model_specialist
        # Otherwise, the model recommended a specialist that contradicts our deterministic keyword match!
        # E.g. symptoms mention "knee pain" (expected: orthopedic) but model says "dermatologist".
        # This is a sharp disagreement, so we default to "general_physician".
        logger.warning(f"Specialist mismatch! Symptoms: '{symptoms_text}'. Expected one of: {detected_specialists}. Model returned: {model_specialist}. Overriding to 'general_physician'.")
        return "general_physician"
        
    return model_specialist


# 3. System Prompt for Triage Loop
SYSTEM_PROMPT = """You are a symptom intake assistant for a healthcare navigation app used in India. You are NOT a doctor and must never give a diagnosis or treatment advice. Your only job is to:
(a) extract structured symptom information from what the user said, and
(b) ask ONE short, clear follow-up question when required information is missing, OR
(c) return a final triage summary once enough information has been gathered or the turn limit is reached.

LANGUAGE RULE: The user will speak in either Hindi or English — no other language is supported. Detect which of these two the input transcript is in, and respond ONLY in that same language, for both the follow-up question and the reasoning_summary. If the transcript is in neither language, default to English and set confidence to "low".

SLOT FIELDS (fill these as the conversation progresses):
- chief_complaint (string)
- body_location (string)
- onset (enum: sudden | gradual | unknown)
- duration (string)
- severity (integer 1-10)
- associated_symptoms (list of strings)
- aggravating_factors (string, optional)

FIELD PRIORITY — when a follow-up is needed, ask about ONLY the first missing field in this order, never more than one field per question:
1. body_location (if not already clear from chief complaint)
2. severity (always ask if missing — needed for urgency scoring)
3. onset / duration
4. associated_symptoms (ask specifically, don't say "anything else?")
5. aggravating_factors (only if turns remain)

RULES:
- Never ask about a field that's already filled.
- Stop asking questions and return triage_complete if turn_count >= max_turns, OR if chief_complaint, body_location, severity, onset, and associated_symptoms are all filled.
- specialist_type must be exactly one of: general_physician | orthopedic | dermatologist | pulmonologist | cardiologist | gastroenterologist | ent | gynecologist | pediatrician | ophthalmologist | psychiatrist
- urgency_level must be exactly one of: emergency | urgent | routine | self_care
- Do not attempt to name a specific disease — only categorize urgency and specialist type.
- If genuinely uncertain about urgency, default to the higher urgency category, not the lower one.

OUTPUT FORMAT:
Respond with ONLY valid JSON, no markdown formatting, no extra text before or after — exactly one of these two shapes.

If more information is needed (status = "follow_up"):
{
  "status": "follow_up",
  "updated_session_state": {
    "chief_complaint": "extracted or merged value, or null",
    "body_location": "extracted or merged value, or null",
    "onset": "sudden | gradual | unknown or null",
    "duration": "extracted or merged value, or null",
    "severity": integer or null,
    "associated_symptoms": ["list of strings"],
    "aggravating_factors": "extracted or merged value, or null"
  },
  "follow_up_question": "one short question, in the detected language (Hindi or English)"
}

If enough information has been gathered OR turn_count >= max_turns (status = "triage_complete"):
{
  "status": "triage_complete",
  "updated_session_state": {
    "chief_complaint": "extracted or merged value, or null",
    "body_location": "extracted or merged value, or null",
    "onset": "sudden | gradual | unknown or null",
    "duration": "extracted or merged value, or null",
    "severity": integer or null,
    "associated_symptoms": ["list of strings"],
    "aggravating_factors": "extracted or merged value, or null"
  },
  "triage_result": {
    "urgency_level": "emergency | urgent | routine | self_care",
    "specialist_type": "general_physician | orthopedic | dermatologist | pulmonologist | cardiologist | gastroenterologist | ent | gynecologist | pediatrician | ophthalmologist | psychiatrist",
    "confidence": "high | moderate | low",
    "red_flags_triggered": [],
    "reasoning_summary": "2-3 sentences, in the detected language (Hindi or English)"
  }
}
"""



def call_gemini_triage(transcript: str, session_state: SessionState, turn_count: int, max_turns: int = 3) -> Dict[str, Any]:
    """
    Executes the Gemini model call using Vertex AI's gemini-2.5-flash.
    Includes a retry block on parse failure as specified.
    """
    input_payload = {
        "transcript": transcript,
        "session_state": session_state.dict(),
        "turn_count": turn_count,
        "max_turns": max_turns
    }
    
    # Format user prompt
    prompt = f"System Prompt:\n{SYSTEM_PROMPT}\n\nInput Context:\n{json.dumps(input_payload, indent=2)}\n\nGenerate the JSON response:"
    
    # We call Gemini with response_mime_type set to json to guarantee clean JSON output
    generation_config = GenerationConfig(
        response_mime_type="application/json",
        temperature=0.1,
    )
    
    # Attempt 1
    try:
        model = GenerativeModel("gemini-2.5-flash")
        logger.info(f"Sending request to Gemini (Turn {turn_count})...")
        response = model.generate_content(prompt, generation_config=generation_config)
        response_text = response.text.strip()
        logger.info(f"Raw response from Gemini: {response_text}")
        
        parsed_response = json.loads(response_text)
        return parsed_response
    except Exception as e:
        logger.warning(f"First attempt to call/parse Gemini failed: {e}. Retrying once...")
        
        # Retry with a direct re-prompt instruction appended
        try:
            retry_prompt = prompt + "\n\nCRITICAL: Your response was invalid. You must respond with EXACTLY valid JSON matching the specified schema, without any markdown code blocks or extra characters."
            model = GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(retry_prompt, generation_config=generation_config)
            response_text = response.text.strip()
            logger.info(f"Raw retry response from Gemini: {response_text}")
            parsed_response = json.loads(response_text)
            return parsed_response
        except Exception as retry_e:
            logger.error(f"Retry attempt failed: {retry_e}. Falling back to default recovery response.")
            
            # Safe recovery fallback
            # If we are below the turn cap, ask for more details. If we hit the cap, force-complete triage with general_physician
            if turn_count < max_turns:
                # Merge current transcript into chief complaint if empty
                updated_state = session_state.dict()
                if not updated_state.get("chief_complaint"):
                    updated_state["chief_complaint"] = transcript
                return {
                    "status": "follow_up",
                    "updated_session_state": updated_state,
                    "follow_up_question": "Could you describe your symptoms in more detail?"
                }
            else:
                updated_state = session_state.dict()
                if not updated_state.get("chief_complaint"):
                    updated_state["chief_complaint"] = transcript
                return {
                    "status": "triage_complete",
                    "updated_session_state": updated_state,
                    "triage_result": {
                        "urgency_level": "routine",
                        "specialist_type": "general_physician",
                        "confidence": "low",
                        "red_flags_triggered": [],
                        "reasoning_summary": "Triage was completed with limited details due to connectivity or communication constraints."
                    }
                }

