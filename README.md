# FRIDAY Music

A Go-based Telegram group voice-chat music bot focused on per-chat playback sessions and a lightweight streaming stack.

## Commands currently implemented

- `/start`, `/help`
- `/play <YouTube URL or search query>` — search/download audio via yt-dlp; can also reply to Telegram media
- `/vplay`, `/vp9play` — reply to a Telegram video
- `/pause`, `/resume`, `/skip`
- `/stop`, `/end`, `/leave`
- `/queue`, `/shuffle`, `/playing`, `/volume 0-200`
- `/loop` — repeat the current track until disabled
- `/loopqueue` — cycle through the queue continuously
- `/remove <number>` — remove an upcoming queue item
- `/clear` — clear upcoming tracks without stopping the current track
- `/stats`, `/participants`

Each group has its own queue/session, so different groups can run separate playback sessions. The queue accepts up to 50 upcoming tracks per group to prevent unbounded memory/disk usage. Downloads use unique filenames to avoid collisions when the same song is requested in parallel. `/clear` removes only upcoming tracks; `/stop` clears the queue and leaves the voice chat.

## Requirements

- Go 1.25.3+ and `yt-dlp`/`ffmpeg`/Deno (included in the Docker image)
- Bot token from @BotFather
- Telegram API ID and API hash from https://my.telegram.org
- A Telegram user/assistant session to join voice chats
- A group with an active voice chat

The streaming layer uses [gortc](https://github.com/AmarnathCJD/gortc) and [gogram](https://github.com/AmarnathCJD/gogram).

## Setup

1. Copy `.env.example` to `.env`.
2. Fill in `BOT_TOKEN`, `API_ID`, `API_HASH`, and `SESSION_STRING`.
3. Optionally set `COOKIES_B64` (base64-encoded Netscape cookies file) or `COOKIES_PATH` if your source requires YouTube cookies. Keep these secret.
4. Never commit `.env`, cookies, or any session files.
5. Run:

```sh
go mod tidy
go run .
```

Add the bot account to the group and make it an administrator with permission to invite users. Start a group voice chat before using playback commands. When `/play`, `/vplay`, or `/vp9play` is used, FRIDAY tries to create a short-lived, single-use invite link and have the assistant user account join the group automatically. This works for public and private supergroups when Telegram permits the bot to create invite links; it is not guaranteed if the bot lacks admin/invite permission, join approval is required, or Telegram restricts the assistant account. The assistant then attempts to join the active voice chat. The `/play` command supports YouTube search queries and HTTP(S) URLs through `yt-dlp`, as well as replies to Telegram media. `/vplay` currently plays replied video media; video URL support is basic and depends on the source format.

## Deployment

A Dockerfile and Railway configuration are included. Set environment variables in the hosting dashboard, and ensure the deployment supports Go 1.25.3+, persistent storage for downloads, and outbound Telegram connectivity. Set `SESSION_STRING` for the assistant user session. Optional `COOKIES_B64` or `COOKIES_PATH` can supply yt-dlp cookies; do not commit either value.

## Roadmap / not implemented yet

Seeking, lyrics, inline controls, admin checks, automatic reconnect, and production soak testing still need to be added. Repeat-current-track is available with `/loop`, repeat-queue with `/loopqueue`, queue shuffle with `/shuffle`, and queue removal/clearing with `/remove` and `/clear`. This repository is an initial working-code foundation, not yet a feature-complete replacement for every existing music bot.

## Upstream licenses

FRIDAY uses the open-source [gortc](https://github.com/AmarnathCJD/gortc) and [gogram](https://github.com/AmarnathCJD/gogram) libraries. See their repositories for license and attribution details.
