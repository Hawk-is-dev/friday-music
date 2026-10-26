<h1 align="center">
    Friday Music Bot
</h1>

<p align="center">
    <a href="https://github.com/urstark/sanyamusic">
        <img src="https://img.shields.io/github/v/release/urstark/sanyamusic?color=black&logo=github&logoColor=black&style=social" alt="Release">
    </a>
</p>

<p align="center">
    <b>Friday Music Bot</b> is a Powerful Telegram Music+Video Bot written in Python using Pyrogram and Py-Tgcalls by which you can stream songs, video and even live streams in your group calls via various sources.
</p>

---

## ⚡️ Features

- **High Quality**: Crystal clear audio
- **Multiple Sources**: YouTube • Spotify
- **Playlists**: Create & Manage
- **Multi-Language**: Multiple Languages
- **Elegant UI**: Modern Interface
- **Admin Controls**: Powerful Commands
- **Lightning Fast**: 1-3s Response
- **Stable**: 99.9% Uptime

For the full list of features, please refer to the [features.txt](docs/features.txt) file.

## 🏷 Commands

Start Friday Bot to see all commands or see [commands.txt](docs/commands.txt) file.

[@FridayMusicBot](https://t.me/FridayMusicBot)

## 🚀 Getting Started

### Deployment

Click the buttons below to deploy on your favorite platform.

[<img src="https://www.herokucdn.com/deploy/button.svg" height="35">](https://dashboard.heroku.com/new?template=https://github.com/urstark/sanyamusic) [<img src="https://railway.com/button.svg" height="35">](https://railway.com/deploy/victorious-passion?referralCode=O3RDoQ&utm_medium=integration&utm_source=template&utm_campaign=generic)

### VPS Deployment

<details>
  <summary><b>Host it on VPS Locally :</b></summary>

#### **Step 1: Update System**

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

#### **Step 2: Install Required Packages**

```bash
sudo apt-get install python3 python3-pip ffmpeg git tmux curl -y
```

#### **Step 3: Install Node.js**

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install nodejs -y && npm i -g npm
sudo apt-get install -y nodejs
```

#### **Step 4: Clone Repository**

```bash
git clone https://github.com/Hawk-is-dev/friday-music
cd friday-music
```

#### **Step 5: Create TMUX Session**

```bash
tmux
```

**Note:** Press `Ctrl+B` then `D` to detach screen

**To Reattach:**
```bash
tmux attach
```

#### **Step 6: Install Virtual Environment Packages**

```bash
sudo apt-get install python3-venv -y
```

#### **Step 7: Create Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate
```

#### **Step 8: Install Python Dependencies**

```bash
pip3 install -U pip
pip3 install -U -r requirements.txt
```

#### **Step 9: Configurations**

If its first time then use `bash scripts/setup` or else use `nano .env`

```bash
bash scripts/setup 
nano .env
```

**Fill in your variables:**

- `API_ID` & `API_HASH` - Get from [my.telegram.org](https://my.telegram.org)
- `BOT_TOKEN` - Get from [@BotFather](https://t.me/BotFather)
- `MONGO_DB_URI` - MongoDB Atlas connection string
- `OWNER_ID` - Your Telegram user ID
- `STRING_SESSION` - Generate pyrogram session string
- `LOGGER_ID` - Log group/channel ID (starting with -100)
- `SUPPORT_GROUP` - Your support group link
- `SUPPORT_CHANNEL` - Your support channel link

**Save:** `Ctrl+X` then `Y` then `Enter`

#### **Step 10: Start Bot**

**Method 1:**
```bash
python3 -m SANYAMUSIC
```
or
```bash
venv/bin/python3 -m SANYAMUSIC
```
**Method 2:**
```bash
bash scripts/start
```

**Detach Tmux:** `Ctrl+B` then `D`

To stop the whole bot, attach tmux first via `tmux attach` then do `CTRL`+`C`.

</details>

## 📑 Support / Assistance

Reach out to the maintainer at:
- **Telegram Support**: [Join Channel](https://t.me/SanyaxSupport)
- **DM Owner**: [DM Owner](https://t.me/urstarkz)

## 🤝 Acknowledgement / Credits

Special thanks to these amazing projects/people which/who help power Friday Music Bot:
- [Pyrogram](https://github.com/pyrogram/pyrogram)
- [Py-Tgcalls](https://github.com/pytgcalls/pytgcalls)
- [Yukki](https://github.com/TeamYukki/YukkiMusicBot) (Original Base)

> **Disclaimer & Credits**
> This project is based on the work by **[Yukki](https://github.com/TeamYukki/YukkiMusicBot)**. While the original base belongs to them, I have spent 7-8 months completely modifying and optimizing it. I have updated the entire codebase to support **Python 3.13** and **Pyrogram v2**, removed bloated features, and made it lightning fast. Almost every file has been heavily modified to make this project modern and stable.

---

<div align="center">

![Repo Size](https://img.shields.io/github/repo-size/urstark/sanyamusic?color=black&logo=github&logoColor=black&style=for-the-badge)
![Issues](https://img.shields.io/github/issues/urstark/sanyamusic?color=black&logo=github&logoColor=black&style=for-the-badge)
![License](https://img.shields.io/github/license/urstark/sanyamusic?color=black&logo=github&logoColor=black&style=for-the-badge)
![Last Commit](https://img.shields.io/github/last-commit/urstark/sanyamusic?color=blue&logo=github&logoColor=green&style=for-the-badge)

<br>

<img src="https://img.shields.io/badge/Made%20with%20%E2%9D%A4%EF%B8%8F%20by-Stark-red?style=for-the-badge&logo=heart" alt="Made with love">

</div>
