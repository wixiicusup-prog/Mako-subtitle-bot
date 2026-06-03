"""
transcribe.py — Transcribe audio using OpenAI Whisper (local, no API key needed).

Model selection via env var WHISPER_MODEL (default: "base").
Supported sizes: tiny, base, small, medium, large
  - tiny/base  → fast, less accurate  (good for cheap servers)
  - small      → balanced
  - medium/large → most accurate, needs more RAM/GPU
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

import whisper  # openai-whisper

logger = logging.getLogger(__name__)

WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL", "base")

# Module-level singleton — load once, reuse across requests
_model = None


def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        logger.info("Loading Whisper model '%s' …", WHISPER_MODEL_NAME)
        _model = whisper.load_model(WHISPER_MODEL_NAME)
        logger.info("Whisper model loaded.")
    return _model


@dataclass
class Segment:
    index: int       # 1-based
    start: float     # seconds
    end: float       # seconds
    text: str        # original transcribed text
    translated: str  # filled in by translate.py


def transcribe_audio(audio_path: Path) -> List[Segment]:
    """
    Transcribe *audio_path* and return a list of timed Segment objects.

    Whisper auto-detects language; we force English task so that
    even non-English speech is transcribed in English (the base for
    subsequent Somali translation).
    """
    model = _get_model()

    logger.info("Starting transcription: %s", audio_path)
    result = model.transcribe(
        str(audio_path),
        task="transcribe",       # keep original language; change to "translate" for en output from any lang
        verbose=False,
        fp16=False,              # safe on CPU-only containers
        condition_on_previous_text=True,
        temperature=0,
    )

    raw_segments = result.get("segments", [])
    segments: List[Segment] = []

    for i, seg in enumerate(raw_segments, start=1):
        text = seg["text"].strip()
        if not text:
            continue
        segments.append(
            Segment(
                index=i,
                start=float(seg["start"]),
                end=float(seg["end"]),
                text=text,
                translated="",
            )
        )

    logger.info("Transcription complete: %d segments", len(segments))
    return segments
