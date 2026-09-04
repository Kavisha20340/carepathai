import logging
import hashlib
import html
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safe imports for Google Cloud clients
try:
    from google.cloud import translate_v2 as translate
except ImportError:
    logger.warning("google-cloud-translate is not installed. Translation services will fall back to Gemini.")
    translate = None

try:
    from google.cloud import firestore
except ImportError:
    logger.warning("google-cloud-firestore is not installed. Translation caching will be bypassed.")
    firestore = None

# Initialize clients
translate_client = None
db = None

if translate is not None:
    try:
        translate_client = translate.Client()
        logger.info("Successfully initialized Google Translation client.")
    except Exception as e:
        logger.warning(f"Google Translation client init failed: {e}. Will use Gemini fallback.")
        translate_client = None

if firestore is not None:
    try:
        db = firestore.Client(project="carepathai")
        logger.info("Successfully initialized Firestore client for translation caching.")
    except Exception as e:
        logger.warning(f"Firestore client init failed: {e}. Caching will be bypassed.")
        db = None


# Firestore collection for caching
CACHE_COLLECTION = "translation_cache"


def translate_via_gemini(text: str, target_language: str) -> str:
    """
    Translates text using Vertex AI Gemini model when Google Translate API client is unavailable.
    """
    try:
        from backend.triage_logic import gemini_model
        if not gemini_model:
            return text
            
        lang_name = "Hindi (Devanagari script)" if target_language == "hi" else "English"
        prompt = (
            f"You are a professional medical translator. Translate the following text accurately into natural, fluent {lang_name}. "
            f"Preserve clinical accuracy. Output ONLY the translation text without quotes or explanations.\n\n"
            f"Text:\n{text}"
        )
        response = gemini_model.generate_content(prompt)
        translated = response.text.strip() if response and response.text else text
        return translated
    except Exception as e:
        logger.error(f"Gemini translation fallback error for '{text[:30]}...': {e}")
        return text


def translate_text(text: str, target_language: str = "hi") -> str:
    """
    Translates a given text string to the target language ('hi' or 'en'), with MD5-hashed Firestore caching
    and Vertex AI Gemini fallback.
    """
    if not text or not isinstance(text, str):
        return text

    text_stripped = text.strip()
    if not text_stripped:
        return text

    # Compute a deterministic 32-char MD5 hash for valid, clean Firestore document IDs
    doc_id = hashlib.md5(text_stripped.lower().encode('utf-8')).hexdigest()

    # 1. Check for a cached translation in Firestore
    if db:
        try:
            cache_ref = db.collection(CACHE_COLLECTION).document(doc_id)
            cached_doc = cache_ref.get()
            if cached_doc.exists:
                cached_data = cached_doc.to_dict()
                if target_language in cached_data:
                    logger.info(f"Translation Cache HIT for '{text_stripped[:25]}...' -> '{cached_data[target_language][:25]}...'")
                    return cached_data[target_language]
        except Exception as cache_err:
            logger.warning(f"Firestore cache read error: {cache_err}")

    # 2. Call Google Translate API or fallback to Gemini
    translated_text = None
    if translate_client:
        try:
            logger.info(f"Calling Google Translate API for '{text_stripped[:25]}...' -> target: {target_language}")
            result = translate_client.translate(text_stripped, target_language=target_language)
            translated_text = result.get("translatedText")
        except Exception as api_err:
            logger.warning(f"Google Translate API error: {api_err}. Using Gemini fallback...")

    if not translated_text or translated_text == text_stripped:
        translated_text = translate_via_gemini(text_stripped, target_language)

    # Clean HTML entities returned by Translate API (e.g. &#39; -> ')
    if translated_text:
        translated_text = html.unescape(translated_text)

    # 3. Store the new translation in Firestore cache
    if db and translated_text:
        try:
            cache_ref = db.collection(CACHE_COLLECTION).document(doc_id)
            cache_ref.set({target_language: translated_text}, merge=True)
            logger.info(f"Stored translation in cache for doc_id '{doc_id}'")
        except Exception as cache_write_err:
            logger.warning(f"Firestore cache write error: {cache_write_err}")

    return translated_text if translated_text else text


async def async_translate_text(text: str, target_language: str = "hi") -> str:
    """
    Asynchronous wrapper for translate_text that offloads execution to thread pool,
    enabling parallel execution of multiple translation tasks via asyncio.gather().
    """
    if not text or not isinstance(text, str) or not text.strip():
        return text
    return await asyncio.to_thread(translate_text, text, target_language)
