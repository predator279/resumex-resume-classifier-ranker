# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — ResumeX
#
# CPU-only PyTorch is installed FIRST via the official CPU wheel index
# to save ~700 MB compared to the default GPU wheel.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Step 1: CPU-only PyTorch (must be before other deps) ─────────────────────
RUN pip install --no-cache-dir \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

# ── Step 2: Remaining Python dependencies ────────────────────────────────────
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# ── Step 3: Copy application code ────────────────────────────────────────────
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# ── Step 4: Expose and run ───────────────────────────────────────────────────
EXPOSE 8000

# HuggingFace cache will be mounted as a Docker volume (see docker-compose.yml)
# so models are downloaded once and persist across container restarts.
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface
ENV HF_HOME=/root/.cache/huggingface

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
