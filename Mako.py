import os
import telebot
import ffmpeg
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator

# =========================
# BOT TOKEN
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN lama helin")

bot = telebot.TeleBot(BOT_TOKEN)

# =========================
# WHISPER MODEL (LIGHT)
# =========================
model = WhisperModel("base", device="cpu", compute_type="int8")

# =========================
# AUDIO EXTRACTION
# =========================
def extract_audio(video_file, audio_file):
    ffmpeg.input(video_file).output(audio_file).run(overwrite_output=True)

# =========================
# SPEECH TO TEXT
# =========================
def transcribe(audio_file):
    segments, _ = model.transcribe(audio_file)

    text = ""
    for s in segments:
        text += s.text + " "

    return text.strip()

# =========================
# TRANSLATION EN → SO
# =========================
def translate(text):
    return GoogleTranslator(source="en", target="so").translate(text)

# =========================
# CREATE SRT FILE
# =========================
def make_srt(text):
    return f"""1
00:00:01,000 --> 00:00:10,000
{text}
"""

# =========================
# START COMMAND
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Soo dir video, subtitle Somali ayaan kuu sameynayaa.")

# =========================
# VIDEO HANDLER
# =========================
@bot.message_handler(content_types=['video'])
def handle_video(message):

    bot.reply_to(message, "⏳ Video waa la shaqeynayaa...")

    # 1. download video
    file_info = bot.get_file(message.video.file_id)
    downloaded = bot.download_file(file_info.file_path)

    video_path = "video.mp4"
    audio_path = "audio.mp3"

    with open(video_path, "wb") as f:
        f.write(downloaded)

    # 2. extract audio
    extract_audio(video_path, audio_path)

    # 3. speech to text
    text = transcribe(audio_path)

    if not text:
        bot.reply_to(message, "❌ Wax cod ah lama helin")
        return

    # 4. translate
    somali = translate(text)

    # 5. create subtitle
    srt = make_srt(somali)

    with open("subtitle.srt", "w", encoding="utf-8") as f:
        f.write(srt)

    # 6. send file
    bot.send_document(message.chat.id, open("subtitle.srt", "rb"))

# =========================
# RUN BOT
# =========================
print("Bot started...")
bot.infinity_polling(skip_pending=True)
