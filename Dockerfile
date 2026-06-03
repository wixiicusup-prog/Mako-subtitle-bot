# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder — install Python deps into a clean venv
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Install build tools needed for some wheels (e.g. cffi, tiktoken)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Create isolated venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — lean final image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Mano Bot" \
      org.opencontainers.image.description="Telegram bot: video → Whisper transcription → Somali SRT" \
      org.opencontainers.image.source="https://github.com/your-org/mano-bot"

# ── System packages ───────────────────────────────────────────────────────────
# ffmpeg: audio extraction
# ca-certificates: HTTPS to Telegram / OpenAI
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── Python environment from builder ──────────────────────────────────────────
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ── App source ────────────────────────────────────────────────────────────────
WORKDIR /app
COPY . .

# ── Runtime settings ──────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Whisper model cache (persisted across restarts if volume-mounted)
    WHISPER_CACHE=/app/.whisper \
    # Default to 'base' model; override via .env / Railway env vars
    WHISPER_MODEL=base \
    TEMP_DIR=/tmp/mano \
    MAX_FILE_SIZE_MB=200

# Create directories
RUN mkdir -p /tmp/mano /app/.whisper

# Non-root user for security
RUN useradd -r -u 1001 -m mano && \
    chown -R mano:mano /app /tmp/mano
USER mano

# Expose nothing — bot uses outbound long-polling only
CMD ["python", "main.py"]
