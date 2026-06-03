# 🎬 Somali Subtitle Bot

A production-ready Telegram bot that automatically generates **Somali subtitles** from any video file.

```
Video → FFmpeg (audio extraction) → Whisper AI (STT) → Translation API → .SRT file
```

---

## ✨ Features

| Feature | Detail |
|---|---|
| 📹 Video input | MP4, MKV, AVI, MOV, WEBM, FLV via Telegram |
| 🎧 Audio extraction | FFmpeg — 16 kHz mono WAV |
| 🧠 Speech-to-text | OpenAI Whisper (any language → auto-detected) |
| 🌍 Translation | English → Somali via Google Translate / LibreTranslate / MyMemory |
| 📄 Output | Standards-compliant `.srt` file |
| 🐳 Deployment | Docker + Docker Compose / Railway / Render |

---

## 🚀 Quick Start

### 1. Create a Telegram Bot

1. Open Telegram → search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy your **bot token**

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN (and optionally GOOGLE_TRANSLATE_API_KEY)
```

### 3. Run with Docker Compose

```bash
docker compose up --build -d
docker compose logs -f   # watch logs
```

That's it! Send a video to your bot on Telegram.

---

## 🌍 Translation Providers

The bot tries providers in this order:

### Option A — Google Cloud Translation ⭐ (Recommended)

Best quality for Somali. Free tier: 500,000 chars/month.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Cloud Translation API**
3. Create an API key → set `GOOGLE_TRANSLATE_API_KEY` in `.env`

### Option B — LibreTranslate (Self-hosted, Free)

Privacy-friendly, no usage limits when self-hosted.

Uncomment the `libretranslate` service in `docker-compose.yml`, then set:
```
LIBRETRANSLATE_URL=http://libretranslate:5000
```

### Option C — MyMemory (Free, No Key)

Automatic fallback. Rate-limited to ~1,000 words/day. Good for testing.

No configuration needed — works out of the box.

---

## 🤖 Whisper Model Selection

| Model | Size | Speed | Accuracy | RAM |
|---|---|---|---|---|
| `tiny` | 39 MB | ⚡⚡⚡ | Good | 1 GB |
| `base` | 74 MB | ⚡⚡ | Better | 1 GB |
| `small` | 244 MB | ⚡ | Great | 2 GB |
| `medium` | 769 MB | 🐢 | Excellent | 5 GB |

Set `WHISPER_MODEL=small` in `.env` for a good speed/quality balance.

---

## ☁️ Deploy to Railway

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app/) → **New Project** → Deploy from GitHub
3. Set environment variables in the Railway dashboard:
   - `TELEGRAM_BOT_TOKEN`
   - `GOOGLE_TRANSLATE_API_KEY` (optional)
   - `WHISPER_MODEL` (default: `base`)
4. Railway auto-builds the Dockerfile and deploys 🎉

**Recommended Railway plan:** Hobby ($5/mo) — provides enough RAM for `base` model.  
For `small` model upgrade to Pro.

---

## ☁️ Deploy to Render

1. Push to GitHub
2. New **Web Service** → connect repo
3. Set **Environment** = Docker
4. Add env vars in Render dashboard
5. Set **Instance Type** to at least **Standard** (2 GB RAM)

---

## 🗂 Project Structure

```
somali-subtitle-bot/
├── bot.py            # Telegram bot + pipeline orchestration
├── transcriber.py    # Whisper AI speech-to-text
├── translator.py     # Multi-provider translation to Somali
├── subtitle.py       # SRT file generation
├── requirements.txt  # Python dependencies
├── Dockerfile        # Multi-stage Docker build
├── docker-compose.yml
├── railway.toml      # Railway deployment config
└── .env.example      # Environment variable template
```

---

## 🛠 Local Development (without Docker)

```bash
# Install FFmpeg
sudo apt install ffmpeg   # Ubuntu/Debian
brew install ffmpeg        # macOS

# Install Python dependencies
pip install -r requirements.txt

# Set env vars
export TELEGRAM_BOT_TOKEN=xxx
export GOOGLE_TRANSLATE_API_KEY=xxx  # optional

# Run
python bot.py
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | From @BotFather |
| `GOOGLE_TRANSLATE_API_KEY` | ⭕ | — | Google Cloud Translation |
| `LIBRETRANSLATE_URL` | ⭕ | — | LibreTranslate base URL |
| `LIBRETRANSLATE_KEY` | ⭕ | — | LibreTranslate API key |
| `WHISPER_MODEL` | ⭕ | `base` | tiny/base/small/medium |
| `MAX_FILE_MB` | ⭕ | `50` | Max video size in MB |
| `TRANSLATION_BATCH_SIZE` | ⭕ | `20` | Segments per API call |

---

## 📝 SRT Output Example

```srt
1
00:00:01,000 --> 00:00:04,200
Waxaan jeclahay Soomaaliya

2
00:00:04,500 --> 00:00:08,100
Luuqadda Soomaaliga waa mid qurux badan
```

Load the `.srt` in **VLC**, **MX Player**, **HandBrake**, or any NLE (DaVinci, Premiere).

---

## 📄 License

MIT
