
import sys
import os
import json
import logging
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path so we can import backend packages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TestClient(app)

# --- GLOBAL DEPENDENCY OVERRIDES FOR AUTH & FIRESTORE TESTING ---
import backend.main as main_module
from backend.auth_logic import verify_id_token

# Mock Firestore DB in memory
MOCK_FIRESTORE_DB = {}

def mock_get_session(session_id: str):
    logger.info(f"MOCK FIRESTORE: get_session({session_id})")
    return MOCK_FIRESTORE_DB.get(session_id)

def mock_update_session(session_id: str, uid: str, session_state: dict, turn_count: int, conversation_history: list, triage_result: dict = None):
    logger.info(f"MOCK FIRESTORE: update_session({session_id})")
    if session_id not in MOCK_FIRESTORE_DB:
        MOCK_FIRESTORE_DB[session_id] = {"uid": uid, "conversation_history": [], "session_state": {}}
    MOCK_FIRESTORE_DB[session_id]["conversation_history"] = conversation_history
    MOCK_FIRESTORE_DB[session_id]["session_state"] = session_state
    if triage_result:
        MOCK_FIRESTORE_DB[session_id]["triage_result"] = triage_result

    return True

# Monkey-patch Firestore methods in main.py
main_module.get_session = mock_get_session
main_module.update_session = mock_update_session

# Override verification dependency globally to bypass live Firebase Auth
app.dependency_overrides[verify_id_token] = lambda: "test_user_123"

# Clear mock db between tests
def clear_mock_db():
    MOCK_FIRESTORE_DB.clear()

# Add fake bearer token to headers globally for the TestClient
client.headers = {"Authorization": "Bearer mock_token_abc"}

def print_separator(title: str):
    print("\n" + "="*80)
    print(f" TEST CASE: {title} ")
    print("="*80)

# --- NEW MEDGEMMA TESTS ---

@patch('backend.reasoning_logic.query_medgemma')
def test_emergency_scenario(mock_query_medgemma):
    print_separator("Emergency Scenario - Chest Pain")
    clear_mock_db()

    mock_query_medgemma.return_value = {
        "urgency": {"level": "Emergency", "justification": "Potential cardiac event."},
        "conversation_status": {"is_complete": True, "next_question_to_user": None, "confidence_score": 0.9},
        "final_summary": {"chief_complaint": "Chest pain", "specialty_recommendation": "Cardiologist", "clinical_reasoning": ""}
    }

    payload = {
        "transcript": "I have severe chest pain",
        "session_id": "emergency_session",
        "turn_count": 1,
        "max_turns": 3
    }

    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "emergency"
    assert "Potential cardiac event." in data["message"]

@patch('backend.reasoning_logic.query_medgemma')
def test_follow_up_scenario(mock_query_medgemma):
    print_separator("Follow-up Scenario - Vague Symptoms")
    clear_mock_db()

    mock_query_medgemma.return_value = {
        "urgency": {"level": "Routine", "justification": ""},
        "conversation_status": {"is_complete": False, "next_question_to_user": "Can you describe the pain?", "confidence_score": 0.4},
        "final_summary": {"chief_complaint": None, "specialty_recommendation": None, "clinical_reasoning": None}
    }

    payload = {
        "transcript": "I have a pain",
        "session_id": "follow_up_session",
        "turn_count": 1,
        "max_turns": 3
    }

    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "follow_up"
    assert "Can you describe the pain?" in data["follow_up_question"]

@patch('backend.reasoning_logic.query_medgemma')
def test_triage_complete_scenario(mock_query_medgemma):
    print_separator("Triage Complete Scenario - Knee Pain")
    clear_mock_db()

    mock_query_medgemma.return_value = {
        "urgency": {"level": "routine", "justification": ""},
        "conversation_status": {"is_complete": True, "next_question_to_user": None, "confidence_score": "high"},
        "final_summary": {"chief_complaint": "Knee pain after a fall", "specialty_recommendation": "orthopedic", "clinical_reasoning": "The patient fell and has knee pain."}
    }

    payload = {
        "transcript": "I fell and my knee hurts",
        "session_id": "complete_session",
        "turn_count": 3,
        "max_turns": 3
    }

    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "triage_complete"
    assert data["triage_result"]["specialist_type"] == "orthopedic"


@patch("backend.main.transcribe_audio")
def test_transcribe_endpoint(mock_transcribe_audio):
    print_separator("Transcribe Endpoint")
    mock_transcribe_audio.return_value = {"transcript": "This is a test"}

    with open("test.wav", "wb") as f:
        f.write(b"\x00\x01\x02\x03")  # Dummy audio data

    with open("test.wav", "rb") as f:
        response = client.post("/transcribe", files={"file": f})

    os.remove("test.wav")

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    assert response.json()["transcript"] == "This is a test"


def test_empty_transcript_handling():
    print_separator("Empty Transcript Handling")
    clear_mock_db()

    payload = {
        "transcript": "   ",
        "session_id": "empty_session",
        "turn_count": 1,
        "max_turns": 3
    }

    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 400
    assert "Transcript text cannot be empty" in response.json()["detail"]


@patch('backend.reasoning_logic.query_medgemma')
def test_null_specialty_recommendation_handling(mock_query_medgemma):
    print_separator("Null Specialty Recommendation Handling")
    clear_mock_db()

    mock_query_medgemma.return_value = {
        "urgency": {"level": "Self-care", "justification": "No fever reported."},
        "conversation_status": {"is_complete": True, "next_question_to_user": None, "confidence_score": 0.9},
        "final_summary": {
            "chief_complaint": "Feeling unwell.",
            "specialty_recommendation": None,
            "clinical_reasoning": "Consider rest."
        }
    }

    payload = {
        "transcript": "I have clearly said before no.",
        "session_id": "null_specialty_session",
        "turn_count": 2,
        "max_turns": 3
    }

    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "triage_complete"
    assert data["triage_result"]["specialist_type"] == "general_physician"


@patch('backend.main.async_translate_text')
def test_translate_results_endpoint(mock_async_translate_text):
    print_separator("Translate Results Endpoint")
    clear_mock_db()

    # Define mock translation behavior: append suffix showing target language
    async def side_effect_translate(text, target_language="hi"):
        return f"{text} [translated: {target_language}]"
    
    mock_async_translate_text.side_effect = side_effect_translate

    # Set up mock session in memory DB
    session_id = "test_trans_session"
    MOCK_FIRESTORE_DB[session_id] = {
        "uid": "test_user_123",
        "turn_count": 3,
        "conversation_history": [],
        "session_state": {
            "chief_complaint": "Knee pain after a fall",
            "body_location": "Knee",
            "onset": "After a fall",
            "duration": "Mild",
            "severity": "Mild",
            "associated_symptoms": ["Pain", "Swelling"],
            "aggravating_factors": None
        },
        "triage_result": {
            "urgency": {"level": "routine"},
            "conversation_status": {"confidence_score": "high"},
            "final_summary": {
                "specialty_recommendation": "orthopedic",
                "clinical_reasoning": "The patient fell and has knee pain."
            }
        }
    }

    # Test 1: Toggle to Hindi (Cache Miss -> Calls Translation)
    response = client.post(f"/translate-results?session_id={session_id}&language=hi")
    print(f"Status Code (HI): {response.status_code}")
    print(f"Response (HI): {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    data = response.json()
    assert "triage_result" in data
    assert "updated_session_state" in data

    # Verify translated fields
    assert data["triage_result"]["reasoning_summary"] == "The patient fell and has knee pain. [translated: hi]"
    assert data["updated_session_state"]["chief_complaint"] == "Knee pain after a fall [translated: hi]"
    assert data["updated_session_state"]["body_location"] == "Knee [translated: hi]"
    assert "Pain [translated: hi]" in data["updated_session_state"]["associated_symptoms"]
    assert "Swelling [translated: hi]" in data["updated_session_state"]["associated_symptoms"]

    # Test 2: Toggle to English (Short-circuits, returns original)
    response_en = client.post(f"/translate-results?session_id={session_id}&language=en")
    print(f"Status Code (EN): {response_en.status_code}")
    print(f"Response (EN): {json.dumps(response_en.json(), indent=2)}")

    assert response_en.status_code == 200
    data_en = response_en.json()
    assert data_en["triage_result"]["reasoning_summary"] == "The patient fell and has knee pain."
    assert data_en["updated_session_state"]["chief_complaint"] == "Knee pain after a fall"
    assert data_en["updated_session_state"]["body_location"] == "Knee"
    assert "Pain" in data_en["updated_session_state"]["associated_symptoms"]
    assert "Swelling" in data_en["updated_session_state"]["associated_symptoms"]

    # Test 3: Session Not Found Handling
    response_missing = client.post("/translate-results?session_id=missing_session&language=hi")
    assert response_missing.status_code == 404

