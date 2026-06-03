"""
srt.py — Build a valid SRT subtitle file from a list of Segment objects.

SRT format:
    <index>
    <HH:MM:SS,mmm> --> <HH:MM:SS,mmm>
    <text line(s)>
    <blank line>
"""

import textwrap
from pathlib import Path
from typing import List

from .transcribe import Segment

# Max characters per subtitle line (wraps longer lines)
MAX_LINE_LENGTH = 42


def _seconds_to_srt_timestamp(seconds: float) -> str:
    """Convert floating-point seconds to SRT timestamp HH:MM:SS,mmm."""
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _wrap_text(text: str, width: int = MAX_LINE_LENGTH) -> str:
    """Wrap text to at most *width* chars per line, keeping natural breaks."""
    lines = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
    return "\n".join(lines) if lines else text


def build_srt(segments: List[Segment], output_path: Path) -> None:
    """
    Write an SRT file to *output_path*.

    Each subtitle block uses the *translated* text if available,
    falling back to *text* (English original) otherwise.

    The index is re-assigned sequentially starting from 1 to guarantee
    a valid, gapless SRT sequence even if Whisper returned discontinuous indices.
    """
    blocks: List[str] = []

    for i, seg in enumerate(segments, start=1):
        content = seg.translated if seg.translated else seg.text
        content = _wrap_text(content)

        start_ts = _seconds_to_srt_timestamp(seg.start)
        end_ts = _seconds_to_srt_timestamp(seg.end)

        # Guard: end must be strictly after start
        if seg.end <= seg.start:
            end_ts = _seconds_to_srt_timestamp(seg.start + 1.0)

        block = f"{i}\n{start_ts} --> {end_ts}\n{content}\n"
        blocks.append(block)

    srt_content = "\n".join(blocks)

    output_path.write_text(srt_content, encoding="utf-8")
