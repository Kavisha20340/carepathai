import logging
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables (.env contains GOOGLE_APPLICATION_CREDENTIALS)
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK safely
db = None
try:
    if not firebase_admin._apps:
        # If GOOGLE_APPLICATION_CREDENTIALS is set in .env or active in shell,
        # initialize_app() automatically uses it natively.
        firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized successfully.")
    
    db = firestore.client()
    logger.info("Firestore client connected successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase / Firestore: {e}. Running in local mock mode.")

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the session state and metadata from Firestore for a given session_id.
    Returns the document dict if found, else None.
    """
    if db is None:
        logger.warning("Firestore is not initialized. get_session returning None.")
        return None
        
    try:
        doc_ref = db.collection("sessions").document(session_id)
        doc = doc_ref.get()
        if doc.exists:
            logger.info(f"Retrieved session document for ID: {session_id}")
            return doc.to_dict()
        else:
            logger.info(f"No existing session document found for ID: {session_id}")
            return None
    except Exception as e:
        logger.error(f"Error fetching session {session_id} from Firestore: {e}", exc_info=True)
        return None

def update_session(session_id: str, uid: str, session_state: dict, turn_count: int, conversation_history: list, triage_result: Optional[dict] = None) -> bool:
    """
    Persists or updates the session document in Firestore.
    Document schema matches: {uid, session_state, turn_count, conversation_history, triage_result, timestamp}
    """
    if db is None:
        logger.warning("Firestore is not initialized. update_session skipping.")
        return False
        
    try:
        doc_ref = db.collection("sessions").document(session_id)
        
        # Build Firestore update payload
        payload = {
            "uid": uid,
            "session_state": session_state,
            "turn_count": turn_count,
            "conversation_history": conversation_history,
            "triage_result": triage_result,
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref.set(payload, merge=True)
        logger.info(f"Successfully updated Firestore session document for ID: {session_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating session {session_id} in Firestore: {e}", exc_info=True)
        return False


