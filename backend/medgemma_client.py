
import requests
import json
import os
import logging
import time

# Get logger
logger = logging.getLogger(__name__)

# Get the MedGemma endpoint from environment variables
MEDGEMMA_API_URL = os.getenv("MEDGEMMA_API_URL", "http://localhost:8080/v1/chat/completions") # Default for local testing

def _repair_json_string(json_str: str) -> str:
    """Attempts to repair truncated JSON strings by closing unclosed quotes and braces."""
    s = json_str.strip()
    if s.endswith("```"):
        s = s[:-3].strip()
    
    in_string = False
    escape = False
    brace_stack = []
    for char in s:
        if escape:
            escape = False
            continue
        if char == '\\' and in_string:
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char in '{[':
                brace_stack.append(char)
            elif char in '}]':
                if brace_stack:
                    brace_stack.pop()

    if in_string:
        s += '"'
    
    while brace_stack:
        opener = brace_stack.pop()
        if opener == '{':
            s += '}'
        elif opener == '[':
            s += ']'
            
    return s

def query_medgemma(prompt: str) -> dict:
    """
    Sends a prompt to the MedGemma model and returns the JSON response.
    """
    payload = {
        'prompt': prompt,
        'max_tokens': 512
    }

    start_time = time.time()
    logger.info(f"===> [OUTGOING API CALL: MedGemma] URL: {MEDGEMMA_API_URL} | Prompt Length: {len(prompt)} chars")
    raw_response_text = ""
    try:
        response = requests.post(MEDGEMMA_API_URL, data=payload, timeout=180)
        response.raise_for_status()
        
        raw_response_text = response.text
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        logger.info(f"<=== [INCOMING API RESPONSE: MedGemma] Latency: {duration_ms:.0f} ms | Raw Response: {raw_response_text}")
        
        response_data = response.json()
        messy_string = response_data.get("response", "")

        if not messy_string or not messy_string.strip():
            logger.error("MedGemma API returned an empty response string.")
            return {"error": "EMPTY_RESPONSE", "message": "MedGemma engine returned an empty response string."}

        # Find the first complete JSON object in the messy string.
        brace_level = 0
        start_index = -1
        for i, char in enumerate(messy_string):
            if char == '{':
                if start_index == -1:
                    start_index = i
                brace_level += 1
            elif char == '}':
                brace_level -= 1
                if brace_level == 0 and start_index != -1:
                    json_string = messy_string[start_index:i+1]
                    return json.loads(json_string)
        
        # If complete match wasn't found, attempt JSON repair on partial response
        if start_index != -1:
            partial_json = messy_string[start_index:]
            repaired = _repair_json_string(partial_json)
            try:
                parsed = json.loads(repaired)
                logger.warning("Successfully repaired incomplete JSON response from MedGemma.")
                return parsed
            except Exception as repair_err:
                logger.error(f"Failed to repair partial JSON string: {repair_err}")

        raise json.JSONDecodeError("Could not find a complete JSON object in the response.", messy_string, 0)

    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error querying MedGemma: {e}")
        return {"error": "REQUESTS_ERROR", "message": str(e)}

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from MedGemma: {e}")
        logger.error(f"Problematic raw response was: {raw_response_text}")
        return {"error": "JSON_DECODE_ERROR", "message": f"Failed to decode JSON: {e}", "raw_response": raw_response_text}

    except Exception as e:
        logger.error(f"An unexpected error occurred while querying MedGemma: {e}", exc_info=True)
        return {"error": "UNEXPECTED_ERROR", "message": str(e)}


