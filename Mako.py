import os
import uuid
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import speech_recognition as sr

BOT_TOKEN = os.getenv("8932095381:AAFi6voobTAdyv3_JzJKtNZGfjPi9JwhCu4")

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me a video 🎬\nI will extract audio and generate subtitles."
    )

# Handle video
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document

    if not video:
        await update.message.reply_text("⚠️ Fadlan video soo dir.")
        return

    file = await context.bot.get_file(video.file_id)

    video_path = f"{uuid.uuid4()}.mp4"
    audio_path = f"{uuid.uuid4()}.wav"

    await file.download_to_drive(video_path)

    await update.message.reply_text("⏳ Video la helay... audio ayaan ka saaraya.")

    # 🎬 Convert video → audio (ffmpeg)
    subprocess.call([
        "ffmpeg", "-i", video_path,
        "-ar", "16000", "-ac", "1",
        audio_path, "-y"
    ])

    await update.message.reply_text("🎧 Audio extracted... transcribing.")

    # 🧠 Speech to text
    recognizer = sr.Recognizer()
    audio_file = sr.AudioFile(audio_path)

    with audio_file as source:
        audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio_data)
    except Exception:
        text = "❌ Could not transcribe audio."

    # 📝 Create simple subtitle (SRT)
    srt_file = f"{uuid.uuid4()}.srt"
    with open(srt_file, "w", encoding="utf-8") as f:
        f.write("1\n00:00:01,000 --> 00:00:10,000\n")
        f.write(text + "\n")

    await update.message.reply_text("✅ Subtitle ready!")

    # send subtitle file
    await update.message.reply_document(document=open(srt_file, "rb"))

    # cleanup
    os.remove(video_path)
    os.remove(audio_path)
    os.remove(srt_file)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
