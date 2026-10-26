<div align="center">
  <img src="https://telegra.ph/file/b7b62dc5ddf7da45ecb32.jpg" alt="Friday Music" width="200" style="border-radius: 50%;" />
  <br><br>
  <h1>🎵 Friday Music Bot</h1>
  <p><strong>A highly advanced, lightning-fast Telegram Music Bot built with Python.</strong></p>
  
  <p>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram" />
    <img src="https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB" />
    <img src="https://img.shields.io/badge/Upstash_Redis-00E676?style=for-the-badge&logo=redis&logoColor=white" alt="Upstash Redis" />
  </p>
</div>

<br />

## 🌟 Overview

Friday Music is a powerful, highly customizable Telegram bot designed to stream high-quality audio and video seamlessly into Telegram Voice Chats. Built with scalability and performance in mind, it handles multiple concurrent streams, caches frequently requested queries, and manages group settings using robust database solutions.

Whether you're looking to play music from YouTube, Spotify, or direct links, Friday Music handles it all with zero lag.

## ✨ Key Features

*   **🎧 Universal Playback:** Streams crystal-clear audio and video directly into your Telegram group's Voice Chat.
*   **🔍 Multi-Source Search:** Instantly fetches music from YouTube, Spotify, Apple Music, and direct HTTP streams using `yt-dlp` and custom APIs.
*   **⚡ Blazing Fast Caching:** Integrates **Upstash Redis** to heavily cache search queries, playback metadata, and session states, reducing API calls and latency.
*   **🗄️ Persistent Database:** Uses **MongoDB (Motor)** for asynchronous database operations to store group configurations, admin lists, and user preferences securely.
*   **🗣️ Text-to-Speech:** Features built-in TTS capabilities utilizing `edge-tts`.
*   **🛡️ Robust Admin Controls:** Complete control over voice chats (play, pause, skip, mute, stop, loop) restricted securely to authorized admins.
*   **☁️ Ready to Deploy:** Pre-configured with `app.json`, `Procfile`, and `Dockerfile` for instant deployment on Heroku, Render, or any VPS.

## 🚀 Technical Stack

*   **Core Language:** [Python 3.9+](https://www.python.org/)
*   **Telegram Framework:** [Kurigram](https://github.com/Kurigram/Kurigram) (Optimized Pyrogram fork)
*   **Voice Chat Streaming:** [Py-TgCalls](https://github.com/pytgcalls/pytgcalls)
*   **Database (NoSQL):** [MongoDB](https://www.mongodb.com/) via `motor`
*   **In-Memory Cache:** [Upstash Redis](https://upstash.com/)
*   **Media Extraction:** `yt-dlp` & `youtube-search-python`

## ⚙️ Installation & Deployment

### 1. The Easy Way (Heroku)
Click the button below to deploy the bot directly to Heroku. You will need your Telegram API keys and Database URLs.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

### 2. Local / VPS Deployment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Hawk-is-dev/friday-music.git
   cd friday-music
   ```

2. **Set up Environment Variables:**
   Rename `sample.env` to `.env` and fill in all the required credentials:
   *   `BOT_TOKEN`: Your Telegram Bot Token.
   *   `API_ID` & `API_HASH`: Your Telegram App keys.
   *   `MONGO_DB_URI`: Your MongoDB connection string.
   *   `UPSTASH_REDIS_URL`: Your Upstash Redis connection string.
   *   `SESSION_NAME`: Your Pyrogram string session for the assistant account.

3. **Install Dependencies:**
   Make sure you have FFmpeg installed on your server (`sudo apt install ffmpeg`).
   ```bash
   pip3 install -U -r requirements.txt
   ```

4. **Start the Bot:**
   ```bash
   python3 -m SANYAMUSIC
   ```

## ⚖️ License

This project is open-sourced under the **GNU General Public License v3.0 (GPLv3)**. 

This means you are absolutely free to use, modify, host, and distribute this bot. However, **any modifications or derivative works must also be open-sourced under the exact same GPLv3 license**, and you must give proper credit to the original author.

---
<div align="center">
  <i>Developed and maintained with passion by Stark.</i>
</div>
