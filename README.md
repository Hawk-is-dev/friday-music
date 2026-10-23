# FRIDAY Music

A Go-based Telegram group voice-chat music bot focused on per-chat playback sessions and a lightweight streaming stack.

## Commands currently implemented

- `/start`, `/help`
- `/play` — reply to a Telegram audio/media message
- `/vplay`, `/vp9play` — reply to a Telegram video
- `/pause`, `/resume`, `/skip`
- `/stop`, `/end`, `/leave`
- `/queue`, `/playing`, `/volume 0-200`
- `/stats`, `/participants`

Each group has its own queue/session, so different groups can run separate playback sessions.

## Requirements

- Go 1.25.3+
- Bot token from @BotFather
- Telegram API ID and API hash from https://my.telegram.org
- A Telegram user/assistant session to join voice chats
- A group with an active voice chat

The streaming layer uses [gortc](https://github.com/AmarnathCJD/gortc) and [gogram](https://github.com/AmarnathCJD/gogram).

## Setup

1. Copy `.env.example` to `.env`.
2. Fill in `BOT_TOKEN`, `API_ID`, `API_HASH`, and `SESSION_STRING`.
3. Never commit `.env` or any session files.
4. Run:

```sh
go mod tidy
go run .
```

Add both the bot account and assistant user account to the group. Start a group voice chat before using playback commands. The `/play` command currently expects a reply to a Telegram media message; YouTube search/URL extraction is not yet implemented.

## Deployment

A Dockerfile and Railway configuration are included. Set environment variables in the hosting dashboard, and ensure the deployment supports Go 1.25.3+, persistent storage for session files if not using a string session, and outbound Telegram connectivity.

## Roadmap / not implemented yet

YouTube search and URL playback, playlists, loop/shuffle, seeking, lyrics, inline controls, admin checks, automatic reconnect, and production soak testing still need to be added. This repository is an initial working-code foundation, not yet a feature-complete replacement for every existing music bot.

## Upstream licenses

FRIDAY uses the open-source [gortc](https://github.com/AmarnathCJD/gortc) and [gogram](https://github.com/AmarnathCJD/gogram) libraries. See their repositories for license and attribution details.
