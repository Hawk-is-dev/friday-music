# FRIDAY Music

A Go-based Telegram group voice-chat music bot focused on per-chat playback sessions and a lightweight streaming stack.

## Commands currently implemented

- `/start`, `/help`
- `/play <YouTube URL or search query>` — search/download audio via yt-dlp; can also reply to Telegram media
- `/vplay`, `/vp9play` — reply to a Telegram video
- `/pause`, `/resume`, `/skip`
- `/stop`, `/end`, `/leave`
- `/queue`, `/shuffle`, `/playing`, `/volume 0-200`
- `/stats`, `/participants`

Each group has its own queue/session, so different groups can run separate playback sessions.

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

Add both the bot account and assistant user account to the group. Start a group voice chat before using playback commands. The `/play` command supports YouTube search queries and HTTP(S) URLs through `yt-dlp`, as well as replies to Telegram media. `/vplay` currently plays replied video media; video URL support is basic and depends on the source format.

## Deployment

A Dockerfile and Railway configuration are included. Set environment variables in the hosting dashboard, and ensure the deployment supports Go 1.25.3+, persistent storage for downloads, and outbound Telegram connectivity. Set `SESSION_STRING` for the assistant user session. Optional `COOKIES_B64` or `COOKIES_PATH` can supply yt-dlp cookies; do not commit either value.

## Roadmap / not implemented yet

Playlists, loop/repeat, seeking, lyrics, inline controls, admin checks, automatic reconnect, and production soak testing still need to be added. Queue shuffle is available with `/shuffle`. This repository is an initial working-code foundation, not yet a feature-complete replacement for every existing music bot.

## Upstream licenses

FRIDAY uses the open-source [gortc](https://github.com/AmarnathCJD/gortc) and [gogram](https://github.com/AmarnathCJD/gogram) libraries. See their repositories for license and attribution details.
