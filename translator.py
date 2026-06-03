"""
translator.py — Translates transcript segments to Somali.

Supports three backends (auto-selected based on available env vars):
  1. Google Cloud Translation API  (GOOGLE_TRANSLATE_API_KEY)
  2. DeepL API                     (DEEPL_API_KEY)   — fallback via Google
  3. LibreTranslate (self-hosted)  (LIBRETRANSLATE_URL)
  4. MyMemory (free, no key)       — final fallback

Set the env var for your preferred provider; the others are tried in order.
"""

import asyncio
import logging
import os
from typing import List, Dict

import httpx

logger = logging.getLogger(__name__)

GOOGLE_API_KEY      = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
LIBRETRANSLATE_URL  = os.getenv("LIBRETRANSLATE_URL", "")      # e.g. http://libretranslate:5000
LIBRETRANSLATE_KEY  = os.getenv("LIBRETRANSLATE_KEY", "")
BATCH_SIZE          = int(os.getenv("TRANSLATION_BATCH_SIZE", "20"))


# ── Provider implementations ──────────────────────────────────────────────────

async def _google_translate(texts: List[str], source: str = "en") -> List[str]:
    """Google Cloud Translation (Basic) v2."""
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {"key": GOOGLE_API_KEY}
    payload = {"q": texts, "source": source, "target": "so", "format": "text"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, params=params, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return [item["translatedText"] for item in data["data"]["translations"]]


async def _libretranslate(texts: List[str], source: str = "en") -> List[str]:
    """LibreTranslate (self-hosted or public instance)."""
    url = f"{LIBRETRANSLATE_URL.rstrip('/')}/translate"
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for text in texts:
            payload = {
                "q": text, "source": source, "target": "so",
                "format": "text", "api_key": LIBRETRANSLATE_KEY,
            }
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            results.append(resp.json()["translatedText"])
    return results


async def _mymemory_translate(texts: List[str], source: str = "en") -> List[str]:
    """MyMemory free translation API (no key required, rate-limited)."""
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for text in texts:
            params = {"q": text, "langpair": f"{source}|so"}
            resp = await client.get("https://api.mymemory.translated.net/get", params=params)
            resp.raise_for_status()
            data = resp.json()
            translated = data.get("responseData", {}).get("translatedText", text)
            results.append(translated)
            # MyMemory is rate-limited; small delay between requests
            await asyncio.sleep(0.3)
    return results


async def _translate_batch(texts: List[str]) -> List[str]:
    """Try providers in priority order, fall back gracefully."""
    if GOOGLE_API_KEY:
        try:
            logger.debug("Using Google Translate for %d texts", len(texts))
            return await _google_translate(texts)
        except Exception as exc:
            logger.warning("Google Translate failed: %s — trying fallback", exc)

    if LIBRETRANSLATE_URL:
        try:
            logger.debug("Using LibreTranslate for %d texts", len(texts))
            return await _libretranslate(texts)
        except Exception as exc:
            logger.warning("LibreTranslate failed: %s — trying fallback", exc)

    # Final fallback — always available
    logger.debug("Using MyMemory (free) for %d texts", len(texts))
    return await _mymemory_translate(texts)


# ── Public API ─────────────────────────────────────────────────────────────────

async def translate_to_somali(segments: List[Dict]) -> List[Dict]:
    """
    Translate all segment texts to Somali.

    Args:
        segments: List of {"start", "end", "text"} dicts from transcriber.

    Returns:
        Same list with "text" replaced by the Somali translation,
        and the original kept in "original_text".
    """
    texts = [seg["text"] for seg in segments]

    # Translate in batches to respect API limits
    translated_texts: List[str] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.info(
            "Translating batch %d–%d of %d segments…",
            i + 1, min(i + BATCH_SIZE, len(texts)), len(texts),
        )
        translated_batch = await _translate_batch(batch)
        translated_texts.extend(translated_batch)

    # Merge back into segment dicts
    result = []
    for seg, so_text in zip(segments, translated_texts):
        result.append({
            "start":         seg["start"],
            "end":           seg["end"],
            "text":          so_text,
            "original_text": seg["text"],
        })

    return result
