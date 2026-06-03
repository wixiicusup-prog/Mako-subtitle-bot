import os
import whisper
import ffmpeg
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from googletrans import Translator
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("8932095381:AAFi6voobTAdyv3_JzJKtNZGfjPi9JwhCu4")

model = whisper.load_model("base")
translator = Translator()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me a video, I will translate subtitles into Somali!"
    )


def extract_audio(video_path, audio_path):
    ffmpeg.input(video_path).output(audio_path).run(overwrite_output=True)


def transcribe(audio_path):
    result = model.transcribe(audio_path)
    return result["text"]


def translate_to_somali(text):
    translated = translator.translate(text, dest="so")
    return translated.text


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document

    file = await video.get_file()
    video_path = "video.mp4"
    audio_path = "audio.mp3"

    await file.download_to_drive(video_path)

    await update.message.reply_text("🎬 Extracting audio...")

    extract_audio(video_path, audio_path)

    await update.message.reply_text("🧠 Transcribing...")

    text = transcribe(audio_path)

    await update.message.reply_text("🌍 Translating to Somali...")

    somali_text = translate_to_somali(text)

    subtitle_file = "subtitle.txt"
    with open(subtitle_file, "w", encoding="utf-8") as f:
        f.write(somali_text)

    await update.message.reply_document(document=open(subtitle_file, "rb"))


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
