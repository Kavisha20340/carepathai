FROM python:3.11-slim

# Build tools needed to compile llama-cpp-python's C++ backend.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Explicit CPU-only build (no CUDA kernels) — keeps the image smaller and
# matches Cloud Run's CPU-only environment.
RUN CMAKE_ARGS="-DGGML_CUDA=off" pip install --no-cache-dir -r requirements.txt

# --- Bake the quantized weights into the image at build time ---
# Text-only now, so no mmproj/vision file is downloaded at all.
# Q5_K_M chosen over Q4_K_M: small models lose proportionally more quality
# to aggressive quantization, and dropping vision freed up the memory
# budget to afford it. If it's gated, pass --build-arg HF_TOKEN=... at build time.
ARG HF_TOKEN=""
ARG MODEL_REPO="unsloth/medgemma-4b-it-GGUF"
ARG MODEL_FILE="medgemma-4b-it-Q5_K_M.gguf"

ENV HF_TOKEN=${HF_TOKEN}
RUN mkdir -p /models && \
    huggingface-cli download ${MODEL_REPO} ${MODEL_FILE} --local-dir /models

COPY main.py .

ENV MODEL_PATH=/models/${MODEL_FILE} \
    N_CTX=2048 \
    N_BATCH=512

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]