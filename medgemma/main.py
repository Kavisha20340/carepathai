import os
from typing import Optional

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from llama_cpp import Llama

# Baked into the image at build time (see Dockerfile).
MODEL_PATH = os.environ.get("MODEL_PATH", "/models/medgemma-4b-it-Q5_K_M.gguf")
N_CTX = int(os.environ.get("N_CTX", "2048"))
N_BATCH = int(os.environ.get("N_BATCH", "512"))
N_THREADS = int(os.environ.get("N_THREADS", str(os.cpu_count() or 4)))

app = FastAPI(title="MedGemma 4B CPU Inference (text-only)")

_llm: Optional[Llama] = None

SYSTEM_PROMPT = (
    "You are MedGemma, a medical AI assistant. Give clear, careful, "
    "medically-informed responses. Be concise — 3-5 short sentences or a "
    "brief bulleted list, not an exhaustive one. You are not a substitute "
    "for professional medical care — advise the user to seek in-person "
    "care for anything urgent or when you are uncertain."
)


def get_llm() -> Llama:
    """Load the model once and reuse it across requests within an instance.

    No chat_format is passed here on purpose: llama-cpp-python will use the
    chat template embedded in the GGUF's own metadata, which is MedGemma's
    actual Gemma-family template (<start_of_turn>/<end_of_turn>) rather than
    an approximation. This is what fixes the hallucinated-turn bug that came
    from using a mismatched LLaVA-style handler.
    """
    global _llm
    if _llm is None:
        _llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=N_CTX,
            n_batch=N_BATCH,
            n_threads=N_THREADS,
            verbose=False,
        )
    return _llm


@app.on_event("startup")
def load_model_on_startup() -> None:
    get_llm()


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _llm is not None}


@app.post("/generate")
async def generate(
    prompt: str = Form(...),
    max_tokens: int = Form(300),
    temperature: float = Form(0.2),
):
    llm = get_llm()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    result = llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        # With the correct native template, the model should emit its own
        # proper end-of-turn token and stop cleanly on its own. These are
        # kept only as a safety net in case of any residual edge cases.
        stop=["<end_of_turn>"],
    )

    response_text = result["choices"][0]["message"]["content"]
    return JSONResponse({"response": response_text, "usage": result.get("usage")})