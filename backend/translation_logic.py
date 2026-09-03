import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safe imports for Google Cloud clients
try:
    from google.cloud import translate_v2 as translate
except ImportError:
    logger.warning("google-cloud-translate is not installed. Translation services will be bypassed.")
    translate = None

try:
    from google.cloud import firestore
except ImportError:
    logger.warning("google-cloud-firestore is not installed. Translation caching will be bypassed.")
    firestore = None

# Initialize clients
translate_client = None
db = None

if translate is not None and firestore is not None:
    try:
        translate_client = translate.Client()
        db = firestore.Client(project="carepathai")
        logger.info("Successfully initialized Google Translation and Firestore clients.")
    except Exception as e:
        logger.error(f"Failed to initialize Google clients: {e}")
        translate_client = None
        db = None


# Firestore collection for caching
CACHE_COLLECTION = "translation_cache"

def translate_text(text: str, target_language: str = "hi") -> str:
    """
    Translates a given text string to the target language, with Firestore caching.

    Args:
        text: The text to translate (expected to be in English).
        target_language: The ISO 639-1 code for the target language (e.g., "hi" for Hindi).

    Returns:
        The translated text. Returns the original text if translation fails or is not needed.
    """
    if not text or not isinstance(text, str) or target_language == "en" or not translate_client or not db:
        return text

    # Use a sanitized version of the text as the Firestore document ID
    # Firestore IDs must be non-empty and not contain slashes.
    doc_id = text.lower().strip().replace("/", "_")
    if not doc_id:
        return text
        
    cache_ref = db.collection(CACHE_COLLECTION).document(doc_id)

    try:
        # 1. Check for a cached translation first
        cached_doc = cache_ref.get()
        if cached_doc.exists:
            cached_data = cached_doc.to_dict()
            if target_language in cached_data:
                logger.info(f"Cache HIT for '{text}' -> '{cached_data[target_language]}'")
                return cached_data[target_language]

        # 2. If not in cache, call the Translation API
        logger.info(f"Cache MISS for '{text}'. Calling Translation API...")
        result = translate_client.translate(text, target_language=target_language)
        translated_text = result["translatedText"]
        logger.info(f"Translation API result: '{text}' -> '{translated_text}'")

        # 3. Store the new translation in the cache
        # Use set with merge=True to create or update the document
        cache_ref.set({target_language: translated_text}, merge=True)
        logger.info(f"Stored new translation in cache: '{doc_id}'")

        return translated_text

    except Exception as e:
        logger.error(f"Error during translation or caching for '{text}': {e}", exc_info=True)
        # In case of any error, fall back to returning the original text
        return text
