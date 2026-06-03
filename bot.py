"""
Somali Subtitle Bot - Telegram bot that generates Somali subtitles from video files.
Pipeline: Video → FFmpeg (audio) → Whisper (STT) → Translation → SRT file
"""

import os
import logging
import asyncio
import tempfile
import subprocess
from pathlib import Path

from telegram import Update, Message
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from transcriber import transcribe_audio
from translator import translate_to_somali
from subtitle import generate_srt

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["8932095381:AAFi6voobTAdyv3_JzJKtNZGfjPi9JwhCu4"]
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "50"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny | base | small | medium


# ── Helpers ───────────────────────────────────────────────────────────────────
async def send_status(msg: Message, text: str) -> Message:
    """Send or edit a status message."""
    return await msg.reply_text(text, parse_mode=ParseMode.HTML)


async def extract_audio(video_path: str, audio_path: str) -> None:
    """Extract mono 16-kHz WAV from video using FFmpeg (subprocess, non-blocking)."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                    # no video
        "-ac", "1",               # mono
        "-ar", "16000",           # 16 kHz — ideal for Whisper
        "-sample_fmt", "s16",
        audio_path,
    ]
    loop = asyncio.get_event_loop()
    proc = await loop.run_in_executor(
        None,
        lambda: subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        ),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\n{proc.stderr[-500:]}")


# ── Handlers ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎬 <b>Somali Subtitle Bot</b>\n\n"
        "Send me a video file (MP4, MKV, AVI, MOV …) and I will:\n"
        "  1️⃣  Extract the audio with FFmpeg\n"
        "  2️⃣  Transcribe speech with Whisper AI\n"
        "  3️⃣  Translate to <b>Somali</b>\n"
        "  4️⃣  Return a <code>.srt</code> subtitle file\n\n"
        f"📦 Max file size: <b>{MAX_FILE_MB} MB</b>\n\n"
        "Just drop your video here to get started!",
        parse_mode=ParseMode.HTML,
    )


async def cmd_help(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 <b>Help</b>\n\n"
        "<b>Supported formats:</b> MP4, MKV, AVI, MOV, WEBM, FLV\n"
        "<b>Languages:</b> detects any → translates to Somali\n"
        "<b>Model:</b> OpenAI Whisper <code>" + WHISPER_MODEL + "</code>\n\n"
        "⚠️ Large files take longer — please be patient!\n"
        "Send /start to see the welcome message again.",
        parse_mode=ParseMode.HTML,
    )


async def handle_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Main pipeline handler for video/document messages."""
    message = update.message

    # ── Resolve file object ───────────────────────────────────────────────────
    file_obj = message.video or message.document
    if file_obj is None:
        await message.reply_text("⚠️ Please send a video file.")
        return

    # ── Size guard ────────────────────────────────────────────────────────────
    file_size_mb = (file_obj.file_size or 0) / (1024 * 1024)
    if file_size_mb > MAX_FILE_MB:
        await message.reply_text(
            f"❌ File is {file_size_mb:.1f} MB — limit is {MAX_FILE_MB} MB.\n"
            "Please compress the video and try again."
        )
        return

    status = await send_status(message, "⏳ Downloading your video…")

    with tempfile.TemporaryDirectory(prefix="subbot_") as tmp:
        tmp = Path(tmp)
        video_path = str(tmp / "input.video")
        audio_path = str(tmp / "audio.wav")
        srt_path   = str(tmp / "subtitles_so.srt")

        try:
            # 1. Download ─────────────────────────────────────────────────────
            tg_file = await ctx.bot.get_file(file_obj.file_id)
            await tg_file.download_to_drive(video_path)
            logger.info("Downloaded %s (%.1f MB)", file_obj.file_id, file_size_mb)

            # 2. Extract audio ─────────────────────────────────────────────────
            await status.edit_text("🎧 Extracting audio with FFmpeg…")
            await extract_audio(video_path, audio_path)
            logger.info("Audio extracted → %s", audio_path)

            # 3. Transcribe ───────────────────────────────────────────────────
            await status.edit_text(
                f"🧠 Transcribing speech with Whisper <code>{WHISPER_MODEL}</code>…\n"
                "This may take a few minutes for long videos.",
                parse_mode=ParseMode.HTML,
            )
            segments = await asyncio.get_event_loop().run_in_executor(
                None, transcribe_audio, audio_path, WHISPER_MODEL
            )
            logger.info("Transcription complete: %d segments", len(segments))

            if not segments:
                await status.edit_text(
                    "⚠️ No speech detected in the video.\n"
                    "Make sure the video has clear audio."
                )
                return

            # 4. Translate ─────────────────────────────────────────────────────
            await status.edit_text("🌍 Translating to Somali…")
            translated = await translate_to_somali(segments)
            logger.info("Translation complete")

            # 5. Generate SRT ──────────────────────────────────────────────────
            await status.edit_text("📄 Generating SRT subtitle file…")
            generate_srt(translated, srt_path)
            logger.info("SRT written → %s", srt_path)

            # 6. Send back ─────────────────────────────────────────────────────
            await status.edit_text("📤 Sending your subtitle file…")
            with open(srt_path, "rb") as f:
                await message.reply_document(
                    document=f,
                    filename="subtitles_somali.srt",
                    caption=(
                        "✅ <b>Somali subtitles ready!</b>\n\n"
                        f"📊 {len(translated)} subtitle segments\n"
                        "Load the <code>.srt</code> file in VLC, MX Player, or your video editor.",
                    ),
                    parse_mode=ParseMode.HTML,
                )
            await status.delete()
            logger.info("SRT delivered to user %s", message.from_user.id)

        except subprocess.TimeoutExpired:
            await status.edit_text("❌ FFmpeg timed out. Try a shorter video.")
        except Exception as exc:
            logger.exception("Pipeline error")
            await status.edit_text(
                f"❌ <b>Error:</b> <code>{str(exc)[:200]}</code>\n\n"
                "Please try again or send a different file.",
                parse_mode=ParseMode.HTML,
            )


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    logger.info("Starting Somali Subtitle Bot (Whisper model: %s)", WHISPER_MODEL)
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))

    # Accept both native Telegram videos and files sent as documents
    app.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.VIDEO | filters.Document.MimeType("video/*"),
            handle_video,
        )
    )

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
