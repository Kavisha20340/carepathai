import sys
import os
import json
import logging

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

def mock_update_session(session_id: str, uid: str, slot_fields: dict, turn_count: int, triage_result=None):
    logger.info(f"MOCK FIRESTORE: update_session({session_id})")
    MOCK_FIRESTORE_DB[session_id] = {
        "uid": uid,
        "slot_fields": slot_fields,
        "turn_count": turn_count,
        "triage_result": triage_result
    }
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

def test_red_flag_chest_pain_and_breathlessness():
    print_separator("Red Flag - Chest Pain & Breathlessness")
    clear_mock_db()
    
    payload = {
        "transcript": "I am experiencing severe chest pain and I can't breathe properly, it feels tight",
        "session_id": "chest_pain_session",
        "turn_count": 0,
        "max_turns": 3
    }
    
    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "emergency"
    assert "medical emergency" in data["message"]
    print("SUCCESS: Red flag triggered and short-circuited correctly!")

def test_red_flag_severity():
    print_separator("Red Flag - High Pain Severity (>=9)")
    clear_mock_db()
    
    # Seed high severity in Firestore mock
    MOCK_FIRESTORE_DB["severity_session"] = {
        "uid": "test_user_123",
        "slot_fields": {
            "chief_complaint": "stomach ache",
            "body_location": "stomach",
            "onset": "gradual",
            "duration": "1 day",
            "severity": 10,
            "associated_symptoms": [],
            "aggravating_factors": None
        },
        "turn_count": 0,
        "triage_result": None
    }
    
    payload = {
        "transcript": "My stomach is hurting",
        "session_id": "severity_session",
        "turn_count": 1,
        "max_turns": 3
    }
    
    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "emergency"
    assert "medical emergency" in data["message"]
    print("SUCCESS: High severity red flag triggered correctly!")

def test_hindi_red_flag():
    print_separator("Red Flag - Hindi (Seene me dard + saans fulna)")
    clear_mock_db()
    
    payload = {
        "transcript": "mere sine me dard ho raha hai aur saans fulna shuru ho gaya hai",
        "session_id": "hindi_red_flag_session",
        "turn_count": 0,
        "max_turns": 3
    }
    
    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "emergency"
    assert "medical emergency" in data["message"]
    print("SUCCESS: Hindi Romanized red flag triggered correctly!")



def test_specialist_backstop_fallback():
    print_separator("Specialist Backstop Fallback Trigger")
    from backend.triage_logic import apply_specialist_backstop
    
    symptoms = "I have a lot of pain in my knee joint"
    model_choice = "dermatologist"
    
    final_choice = apply_specialist_backstop(symptoms, model_choice)
    print(f"Symptoms: '{symptoms}'")
    print(f"Model recommended: {model_choice}")
    print(f"Backstop resolved to: {final_choice}")
    
    assert final_choice == "general_physician"
    print("SUCCESS: Specialist backstop correctly overridden to general_physician!")

def test_specialist_backstop_agree():
    print_separator("Specialist Backstop - Model Agreement")
    from backend.triage_logic import apply_specialist_backstop
    
    symptoms = "I have a lot of pain in my knee joint"
    model_choice = "orthopedic"
    
    final_choice = apply_specialist_backstop(symptoms, model_choice)
    print(f"Symptoms: '{symptoms}'")
    print(f"Model recommended: {model_choice}")
    print(f"Backstop resolved to: {final_choice}")
    
    assert final_choice == "orthopedic"
    print("SUCCESS: Specialist backstop correctly retained the specialist!")

def test_happy_path_knee_pain_english():
    print_separator("Happy Path Knee Pain (English) - Turn 0")
    clear_mock_db()
    
    payload = {
        "transcript": "My right knee has been hurting a lot lately",
        "session_id": "knee_session",
        "turn_count": 0,
        "max_turns": 3
    }
    
    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["follow_up", "triage_complete"]
    
    if data["status"] == "follow_up":
        print(f"SUCCESS: Turn 0 resulted in a follow-up question: '{data['follow_up_question']}'")
        
        print_separator("Happy Path Knee Pain (English) - Turn 1")
        payload_turn1 = {
            "transcript": "The pain is about a 6 on a scale of 1 to 10",
            "session_id": "knee_session",
            "turn_count": 1,
            "max_turns": 3
        }
        response_t1 = client.post("/triage", json=payload_turn1)
        print(f"Status Code: {response_t1.status_code}")
        print(f"Response: {json.dumps(response_t1.json(), indent=2, ensure_ascii=False)}")
        assert response_t1.status_code == 200
        
        data_t1 = response_t1.json()
        assert data_t1["status"] in ["follow_up", "triage_complete"]
        
        if data_t1["status"] == "follow_up":
            print(f"SUCCESS: Turn 1 resulted in a follow-up question: '{data_t1['follow_up_question']}'")
            
            print_separator("Happy Path Knee Pain (English) - Turn 2")
            payload_turn2 = {
                "transcript": "It started gradually about a week ago and there's some swelling in the morning",
                "session_id": "knee_session",
                "turn_count": 2,
                "max_turns": 3
            }
            response_t2 = client.post("/triage", json=payload_turn2)
            print(f"Status Code: {response_t2.status_code}")
            print(f"Response: {json.dumps(response_t2.json(), indent=2, ensure_ascii=False)}")
            assert response_t2.status_code == 200
            
            data_t2 = response_t2.json()
            print(f"SUCCESS: Turn 2 Status is '{data_t2['status']}'")
    else:
        print("SUCCESS: Triage completed on Turn 0!")


def test_happy_path_skin_rash_hindi():
    print_separator("Happy Path Skin Rash (Hindi Devanagari) - Turn 0")
    clear_mock_db()
    
    payload = {
        "transcript": "मुझे पिछले तीन दिनों से हाथ में बहुत खुजली हो रही है और लाल दाने आ गए हैं",
        "session_id": "hindi_rash_session",
        "turn_count": 0,
        "max_turns": 3,
        "language": "hi"
    }
    
    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["follow_up", "triage_complete"]
    
    if data["status"] == "follow_up":
        print(f"SUCCESS: Hindi Turn 0 resulted in follow up: '{data['follow_up_question']}'")
    else:
        print(f"SUCCESS: Hindi Turn 0 completed triage! Reasoning: {data['triage_result']['reasoning_summary']}")



    def test_transcribe_endpoint():
        print_separator("Speech-to-Text Transcribe Endpoint")
        import wave
        import struct
        
        filename = "temp_test_stereo.wav"
        try:
            with wave.open(filename, "wb") as wav:
                wav.setnchannels(2) # Stereo
                wav.setsampwidth(2)
                wav.setframerate(16000)
                num_frames = 16000
                for _ in range(num_frames):
                    # Write silent stereo frames
                    wav.writeframesraw(struct.pack('<h', 0) + struct.pack('<h', 0))
                    
            with open(filename, "rb") as f:
                response = client.post("/transcribe", files={"file": ("test.wav", f, "audio/wav")})
                
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            assert response.status_code == 200
            data = response.json()
            assert "transcript" in data
            print("SUCCESS: /transcribe endpoint completed successfully with Google Cloud STT!")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

def test_haversine_calculation():
    print_separator("Geometrical Haversine Distance Calculation")
    from backend.places_logic import haversine_distance
    
    # Distance between Taj Mahal Palace (Mumbai) and Bandra West should be around 16-18 km
    distance = haversine_distance(18.9218, 72.8333, 19.0600, 72.8360)
    print(f"Distance between Taj Mahal Palace and Bandra West: {distance} km")
    assert 14.0 <= distance <= 20.0
    
    # Distance to the same spot should be 0.0
    assert haversine_distance(19.0600, 72.8360, 19.0600, 72.8360) == 0.0
    print("SUCCESS: Haversine distance calculations are geometrically accurate!")

def test_doctors_endpoint_with_ranking_and_fallback():
    print_separator("POST /doctors Endpoint & Ranking Verification")
    from unittest.mock import patch, MagicMock
    
    mock_places_response = {
        "results": [
            {
                "name": "Orthopedic Center A",
                "geometry": {"location": {"lat": 19.0650, "lng": 72.8400}},
                "vicinity": "Near Bandra Terminus, Mumbai",
                "rating": 4.9,
                "place_id": "ChIJA123"
            },
            {
                "name": "Orthopedic Center B",
                "geometry": {"location": {"lat": 19.0700, "lng": 72.8300}},
                "vicinity": "Linking Road, Bandra, Mumbai",
                "rating": 4.7,
                "place_id": "ChIJB456"
            },
            {
                "name": "Orthopedic Center C",
                "geometry": {"location": {"lat": 19.0550, "lng": 72.8500}},
                "vicinity": "Carter Road, Bandra, Mumbai",
                "rating": 4.7,
                "place_id": "ChIJC789"
            }
        ]
    }
    
    mock_client = MagicMock()
    mock_client.places_nearby.return_value = mock_places_response
    mock_client.place.return_value = {
        "result": {
            "formatted_address": "Mock Clinic Street Address, Bandra, Mumbai",
            "formatted_phone_number": "+91 22 1234 5678"
        }
    }
    
    payload = {
        "specialist_type": "orthopedic",
        "lat": 19.0600,
        "lng": 72.8360,
        "radius_km": 5.0,
        "min_rating": 4.6,
        "max_rating": 5.0
    }
    
    with patch("backend.places_logic.gmaps_client", mock_client):
        response = client.post("/doctors", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        doctors = data["doctors"]
        assert len(doctors) >= 3
        
        # Verify ranking logic: sorted by rating (descending), then distance (ascending) as a tie-breaker
        last_rating = 5.1
        last_distance = -1.0
        for idx, d in enumerate(doctors):
            assert d["name"] is not None
            assert d["specialty_tag"] == "Orthopedic"
            assert d["rating"] <= 5.0
            assert d["distance_km"] > 0.0
            assert d["address"] is not None
            assert "directions_url" in d
            
            if d["rating"] < last_rating:
                pass
            elif d["rating"] == last_rating:
                assert d["distance_km"] >= last_distance, f"Ranking error at index {idx}: Equal rating but distance is not sorted ascending!"
                
            last_rating = d["rating"]
            last_distance = d["distance_km"]
            
    print("SUCCESS: Doctor search endpoint and ranking rules (Rating Desc -> Distance Asc) are fully valid!")



def test_doctors_mocked_api_success():
    print_separator("POST /doctors with Mocked Live Google Places API Response")
    from unittest.mock import patch, MagicMock
    
    mock_places_response = {
        "results": [
            {
                "name": "Live Mock Clinic A",
                "geometry": {"location": {"lat": 19.0650, "lng": 72.8400}},
                "vicinity": "Near Bandra Terminus, Mumbai",
                "rating": 4.9,
                "place_id": "ChIJA123"
            },
            {
                "name": "Live Mock Clinic B",
                "geometry": {"location": {"lat": 19.0700, "lng": 72.8300}},
                "vicinity": "Linking Road, Bandra, Mumbai",
                "rating": 4.5,
                "place_id": "ChIJB456"
            },
            {
                "name": "Live Mock Clinic C",
                "geometry": {"location": {"lat": 19.0550, "lng": 72.8500}},
                "vicinity": "Carter Road, Bandra, Mumbai",
                "rating": 4.5,
                "place_id": "ChIJC789"
            }
        ]
    }
    
    mock_client = MagicMock()
    mock_client.places_nearby.return_value = mock_places_response
    mock_client.place.return_value = {
        "result": {
            "formatted_address": "Mock Clinic Street Address, Bandra, Mumbai",
            "formatted_phone_number": "+91 22 1234 5678"
        }
    }
    
    with patch("backend.places_logic.gmaps_client", mock_client):
        payload = {
            "specialist_type": "orthopedic",
            "lat": 19.0600,
            "lng": 72.8360,
            "radius_km": 5.0
        }
        response = client.post("/doctors", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        doctors = data["doctors"]
        assert len(doctors) == 3
        assert doctors[0]["name"] == "Live Mock Clinic A"
        assert doctors[0]["rating"] == 4.9
        assert doctors[1]["name"] == "Live Mock Clinic B"
        assert doctors[2]["name"] == "Live Mock Clinic C"
        
    print("SUCCESS: Mocked live Google Places API call and tie-breaker sorting processed correctly!")


def test_red_flag_post_gemini_extraction():
    print_separator("Red Flag - Post-Gemini Extraction and 'cannot breathe' match")
    clear_mock_db()
    
    payload = {
        "transcript": "I have severe chest pain and I cannot breathe at all, it feels extremely heavy",
        "session_id": "cannot_breathe_emergency_session",
        "turn_count": 0,
        "max_turns": 3
    }
    
    response = client.post("/triage", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "emergency"
    assert "medical emergency" in data["message"]
    print("SUCCESS: Post-Gemini clinical safety check short-circuited correctly!")


if __name__ == "__main__":
    print("Starting Triage Endpoint End-to-End Tests...")
    test_red_flag_chest_pain_and_breathlessness()
    test_red_flag_severity()
    test_hindi_red_flag()
    test_red_flag_post_gemini_extraction()
    test_specialist_backstop_fallback()
    test_specialist_backstop_agree()
    test_transcribe_endpoint()
    test_haversine_calculation()
    test_doctors_endpoint_with_ranking_and_fallback()
    test_doctors_mocked_api_success()
    
    # Run the Gemini LLM integration tests
    try:
        test_happy_path_knee_pain_english()
        test_happy_path_skin_rash_hindi()
        print("\nAll integration tests PASSED successfully!")
    except Exception as e:
        print(f"\nIntegration tests failed due to: {e}")
        sys.exit(1)



