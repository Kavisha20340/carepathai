import logging
import hashlib
import html
import asyncio
import os

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
genai_client = None

try:
    from google import genai
    project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if project_id:
        genai_client = genai.Client(vertexai=True, project=project_id, location="asia-south1")
    else:
        genai_client = genai.Client(vertexai=True, location="asia-south1")
    # Quick probe test
    genai_client.models.generate_content(model="gemini-3.5-flash", contents="ping")
    logger.info("Successfully initialized Vertex AI Gemini 2.5 Flash client.")
except Exception as gem_err:
    logger.info(f"Vertex AI Gemini client init failed: {gem_err}. Will fallback gracefully.")
    genai_client = None

if translate is not None:
    try:
        translate_client = translate.Client()
        logger.info("Successfully initialized Google Translation client.")
    except Exception as e:
        logger.warning(f"Google Translation client init failed: {e}. Will use Gemini fallback.")
        translate_client = None

if firestore is not None:
    try:
        project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        db = firestore.Client(project=project_id) if project_id else firestore.Client()
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
    if not genai_client:
        return text
    try:
        lang_name = "Hindi (Devanagari script)" if target_language == "hi" else "English"
        prompt = (
            f"You are a professional medical translator. Translate the following text accurately into natural, fluent {lang_name}. "
            f"Preserve clinical accuracy. Output ONLY the translation text without quotes or explanations.\n\n"
            f"Text:\n{text}"
        )
        response = genai_client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
        translated = response.text.strip() if response and response.text else text
        return translated
    except Exception as e:
        logger.error(f"Gemini translation fallback error for '{text[:30]}...': {e}")
        return text


def denoise_transcript_with_context(raw_transcript: str, conversation_history: list = None, language: str = 'en') -> str:
    """
    Uses Gemini Flash to perform rapid, context-aware acoustic denoising and correction on raw STT transcripts.
    Corrects STT misrecognitions (e.g. 'climbing D stears' -> 'climbing the stairs', 'stretch' -> 'strenuous')
    using the full conversation history context. Returns clean, clinical intent text.
    """
    if not raw_transcript or not raw_transcript.strip():
        return raw_transcript

    if not genai_client:
        return raw_transcript

    try:
        history_str = "\n".join(conversation_history) if conversation_history else "None"
        lang_name = "Hindi (Devanagari script)" if language == "hi" else "English"
        
        prompt = (
            f"You are an expert clinical STT transcript denoiser.\n"
            f"Fix acoustic speech-to-text typos, misheard words, and accent distortions in the raw transcript using the conversation history for context.\n\n"
            f"CONVERSATION HISTORY:\n{history_str}\n\n"
            f"RAW STT TRANSCRIPT:\n\"{raw_transcript}\"\n\n"
            f"RULES:\n"
            f"1. Fix misheard words based on medical and conversational context (e.g. 'climbing D stears' -> 'climbing the stairs', 'stretch exercise' -> 'strenuous exercise', 'Vel' -> 'well').\n"
            f"2. Preserve exact patient meaning without changing reported symptoms or hallucinating new symptoms.\n"
            f"3. Output language MUST be {lang_name}.\n"
            f"4. Output ONLY the cleaned transcript string. No quotes, markdown, or explanations.\n"
        )
        logger.info(f"===> [OUTGOING API CALL: Gemini STT Denoiser] Raw: '{raw_transcript}' | Lang: '{language}'")
        response = genai_client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
        if response and response.text:
            cleaned = response.text.strip().strip('"').strip("'")
            logger.info(f"<=== [INCOMING API RESPONSE: Gemini STT Denoiser] Denoised: '{cleaned}'")
            return cleaned
        return raw_transcript
    except Exception as e:
        logger.warning(f"Transcript denoising error: {e}. Returning raw transcript.")
        return raw_transcript


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


try:
    from google.cloud import speech
except ImportError:
    logger.warning("google-cloud-speech is not installed. Transcription services will be unavailable.")
    speech = None

speech_client = speech.SpeechClient() if speech else None

def transcribe_audio(audio_file, language: str = "en") -> dict:
    """
    Transcribes an audio file to text using Google Cloud Speech-to-Text API.
    Uses clean acoustic decoding with latest_long model.
    """
    if not speech_client:
        raise HTTPException(status_code=500, detail="Speech-to-Text service is not configured.")

    content = audio_file.read()
    if not content or len(content) < 10:
        return {"transcript": ""}

    audio = speech.RecognitionAudio(content=content)

    primary_lang = "hi-IN" if language == "hi" else "en-IN"

    # Use "latest_long" for full multi-sentence clinical dictation across BOTH languages.
    # We do NOT use alternative_language_codes to prevent the API from auto-switching
    # English speech into Devanagari script.
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        language_code=primary_lang,
        model="latest_long",
        audio_channel_count=2,
        enable_automatic_punctuation=True,
    )

    logger.info(f"===> [OUTGOING API CALL: Google Speech-to-Text] Lang Code: '{primary_lang}' | Audio Size: {len(content)} bytes")
    
    try:
        response = speech_client.recognize(config=config, audio=audio, timeout=30.0)

        # Extract and join all transcribed sentence segments across the entire audio recording
        transcripts = []
        if response.results:
            for result in response.results:
                if result.alternatives:
                    transcripts.append(result.alternatives[0].transcript.strip())
        transcript = " ".join(transcripts).strip()

        logger.info(f"<=== [INCOMING API RESPONSE: Google Speech-to-Text] Transcribed: '{transcript}'")
        return {"transcript": transcript}
    except Exception as stt_err:
        logger.error(f"Google Speech-to-Text API timeout or error: {stt_err}")
        return {"transcript": ""}

