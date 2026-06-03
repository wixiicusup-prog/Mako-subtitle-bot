"""
audio.py — Extract audio from a video file using FFmpeg.
Output: 16 kHz mono WAV (optimal for Whisper).
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_audio(video_path: Path, audio_path: Path) -> None:
    """
    Run FFmpeg to pull audio out of *video_path* and write a
    16 kHz, mono, 16-bit PCM WAV to *audio_path*.

    Raises:
        RuntimeError: if FFmpeg exits with a non-zero status.
    """
    cmd = [
        "ffmpeg",
        "-y",                       # overwrite without prompting
        "-i", str(video_path),      # input file
        "-vn",                      # drop video stream
        "-ar", "16000",             # sample rate → 16 kHz
        "-ac", "1",                 # mono channel
        "-c:a", "pcm_s16le",        # 16-bit little-endian PCM
        str(audio_path),
    ]

    logger.debug("FFmpeg command: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600,  # 10-minute guard for very long videos
    )

    if result.returncode != 0:
        stderr_text = result.stderr.decode(errors="replace")
        raise RuntimeError(
            f"FFmpeg failed (exit {result.returncode}):\n{stderr_text[-2000:]}"
        )

    logger.info("Audio extracted: %s (%.1f MB)", audio_path, audio_path.stat().st_size / 1_048_576)
