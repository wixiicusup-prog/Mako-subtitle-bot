import os
import ffmpeg
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me a video, I will generate Somali subtitles for you."
    )


# ---------- EXTRACT AUDIO ----------
def extract_audio(video_path, audio_path):
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, format="mp3")
        .overwrite_output()
        .run()
    )


# ---------- TRANSCRIBE (OPENAI WHISPER API) ----------
def transcribe(audio_path):
    with open(audio_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return result.text


# ---------- TRANSLATE TO SOMALI ----------
def translate_to_somali(text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Translate everything to Somali clearly and naturally."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content


# ---------- HANDLE VIDEO ----------
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document

    file = await video.get_file()

    video_path = "video.mp4"
    audio_path = "audio.mp3"

    await file.download_to_drive(video_path)

    await update.message.reply_text("🎬 Extracting audio...")

    extract_audio(video_path, audio_path)

    await update.message.reply_text("🧠 Transcribing...")

    text = await asyncio.to_thread(transcribe, audio_path)

    await update.message.reply_text("🌍 Translating to Somali...")

    somali_text = await asyncio.to_thread(translate_to_somali, text)

    with open("subtitle.txt", "w", encoding="utf-8") as f:
        f.write(somali_text)

    await update.message.reply_document(document=open("subtitle.txt", "rb"))


# ---------- MAIN ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
