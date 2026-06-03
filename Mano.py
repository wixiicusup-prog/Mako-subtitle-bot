"""
Mano Bot — Video → Audio → Whisper Transcription → Somali Translation → SRT
"""

import asyncio
import logging
import os
import tempfile
import uuid
from pathlib import Path

from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .audio import extract_audio
from .transcribe import transcribe_audio
from .translate import translate_to_somali
from .srt import build_srt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN: str = os.environ["8932095381:AAFe_0H_JiSDAFsTqoZ23dXKqgbWQ9aPNuk"]
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
TEMP_DIR: Path = Path(os.getenv("TEMP_DIR", "/tmp/mano"))

TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *Mano Bot* — Subtitle Generator\n\n"
        "Send me any video file and I will:\n"
        "1️⃣ Extract its audio\n"
        "2️⃣ Transcribe speech with Whisper AI\n"
        "3️⃣ Translate English → Somali\n"
        "4️⃣ Return a ready-to-use *.srt* subtitle file\n\n"
        f"📦 Max file size: {MAX_FILE_SIZE_MB} MB",
        parse_mode=constants.ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *How to use Mano Bot*\n\n"
        "• Send a video (MP4, MKV, AVI, MOV, WebM …)\n"
        "• Wait while I process it — large files take a few minutes\n"
        "• Receive your *.srt* subtitle file\n\n"
        "Commands:\n"
        "/start — Welcome message\n"
        "/help  — This help text",
        parse_mode=constants.ParseMode.MARKDOWN,
    )


async def handle_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message

    # Resolve the Telegram file object (video or document)
    tg_file_obj = message.video or message.document
    if tg_file_obj is None:
        await message.reply_text("⚠️ Please send a video file.")
        return

    # File-size guard
    if tg_file_obj.file_size and tg_file_obj.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await message.reply_text(
            f"❌ File too large. Maximum allowed size is {MAX_FILE_SIZE_MB} MB."
        )
        return

    job_id = uuid.uuid4().hex[:8]
    work_dir = TEMP_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    status_msg = await message.reply_text("⏳ Downloading your video…")

    try:
        # ── 1. Download ───────────────────────────────────────────────────────
        original_name = getattr(tg_file_obj, "file_name", None) or "video.mp4"
        video_path = work_dir / original_name
        tg_file = await ctx.bot.get_file(tg_file_obj.file_id)
        await tg_file.download_to_drive(str(video_path))
        logger.info("[%s] Downloaded → %s", job_id, video_path)

        # ── 2. Extract audio ──────────────────────────────────────────────────
        await status_msg.edit_text("🎵 Extracting audio…")
        audio_path = work_dir / "audio.wav"
        await asyncio.to_thread(extract_audio, video_path, audio_path)
        logger.info("[%s] Audio extracted → %s", job_id, audio_path)

        # ── 3. Transcribe ─────────────────────────────────────────────────────
        await status_msg.edit_text("🧠 Transcribing speech (this may take a while)…")
        segments = await asyncio.to_thread(transcribe_audio, audio_path)
        logger.info("[%s] Transcribed %d segments", job_id, len(segments))

        if not segments:
            await status_msg.edit_text("⚠️ No speech detected in the video.")
            return

        # ── 4. Translate ──────────────────────────────────────────────────────
        await status_msg.edit_text("🌍 Translating to Somali…")
        segments = await asyncio.to_thread(translate_to_somali, segments)
        logger.info("[%s] Translation done", job_id)

        # ── 5. Build SRT ──────────────────────────────────────────────────────
        srt_path = work_dir / f"{Path(original_name).stem}_so.srt"
        build_srt(segments, srt_path)
        logger.info("[%s] SRT written → %s", job_id, srt_path)

        # ── 6. Send back ──────────────────────────────────────────────────────
        await status_msg.edit_text("📤 Uploading subtitle file…")
        with open(srt_path, "rb") as f:
            await message.reply_document(
                document=f,
                filename=srt_path.name,
                caption=(
                    f"✅ *Done!*  `{srt_path.name}`\n"
                    f"📝 {len(segments)} subtitle entries • English → Somali"
                ),
                parse_mode=constants.ParseMode.MARKDOWN,
            )
        await status_msg.delete()
        logger.info("[%s] Delivered to user", job_id)

    except Exception as exc:
        logger.exception("[%s] Processing failed: %s", job_id, exc)
        await status_msg.edit_text(
            f"❌ Something went wrong:\n`{exc}`\n\nPlease try again.",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
    finally:
        # Clean up temp files
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))

    # Accept video messages AND documents that look like video
    video_filter = filters.VIDEO | (
        filters.Document.MimeType("video/mp4")
        | filters.Document.MimeType("video/x-matroska")
        | filters.Document.MimeType("video/avi")
        | filters.Document.MimeType("video/quicktime")
        | filters.Document.MimeType("video/webm")
        | filters.Document.MimeType("video/x-msvideo")
        | filters.Document.MimeType("video/mpeg")
    )
    app.add_handler(MessageHandler(video_filter, handle_video))

    logger.info("Mano Bot is running…")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
