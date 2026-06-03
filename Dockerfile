# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ make \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a local directory (for clean copy)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="Somali Subtitle Bot"
LABEL description="Telegram bot: Video → Whisper STT → Somali translation → SRT"

# System dependencies: FFmpeg + libgomp (required by torch)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgomp1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application source
COPY bot.py transcriber.py translator.py subtitle.py ./

# Create temp directory with correct permissions
RUN mkdir -p /tmp/subbot && chmod 777 /tmp/subbot

# Non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Whisper model cache lives in user home
ENV WHISPER_CACHE=/home/botuser/.cache/whisper
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ── Health / pre-download Whisper model at build time ─────────────────────────
# Comment out the ARG + RUN block below to skip pre-downloading (smaller image,
# but first run will download the model which takes a few minutes).
ARG WHISPER_MODEL_PREBUILD=base
RUN python -c "import whisper; whisper.load_model('${WHISPER_MODEL_PREBUILD}')"

CMD ["python", "bot.py"]
