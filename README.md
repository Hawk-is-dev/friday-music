# FRIDAY Music

FRIDAY is a Go-based Telegram voice-chat music bot built with Gogram and Gortc. It uses FFmpeg, yt-dlp, and Deno for media extraction and audio processing.

## Music features

- /play <song name or URL> — play audio; can also reply to Telegram audio/media
- /vplay <URL or reply> and /vp9play <URL or reply> — video playback
- /pause, /resume, /skip, /stop, /end, /leave
- /queue, /playing, /shuffle, /volume 0-200
- /loop, /loopqueue, /remove <number>, /clear
- /mute, /unmute
- /stats, /participants
- /start, /help
- /gensession — owner-only assistant-session setup in private chat

Playback is isolated per group. The now-playing card uses the source thumbnail when available and provides inline pause/resume, repeat, skip, stop, queue, and help controls. The start panel supports an add-to-group button and optional support links.

## Railway variables

Required:
- BOT_TOKEN — token from BotFather
- API_ID and API_HASH — from my.telegram.org
- STRING_SESSION — assistant user session for voice-chat playback. SESSION_STRING is accepted as a compatibility alias.

Optional:
- BOT_NAME — display name, default FRIDAY
- START_IMG_URL — welcome image URL
- SUPPORT_CHANNEL and SUPPORT_CHAT — links shown on the start panel
- COOKIES_B64 or COOKIES_PATH — optional YouTube cookies, if required
- DOWNLOAD_DIR — defaults to downloads
- LOG_LEVEL — defaults to info
- MAX_DURATION_MINUTES — defaults to 30, accepted range 1–240

The owner ID used by /gensession is configured in code, so you do not need an OWNER_ID variable. The original Sanya project has additional variables for MongoDB/Redis, AI tools, playlists, and administration features that this music-focused Go implementation does not currently use.

## Setup

1. Set the required Railway variables.
2. Start FRIDAY and open its private chat as the configured owner.
3. Run /gensession, then follow /sessionphone, /sessioncode, and /sessionpassword prompts if two-step verification is enabled.
4. Copy the generated value to STRING_SESSION and restart the service.
5. Add the bot to a group, make it an admin with permission to invite users, and start a voice chat before playing music.

## Media extraction

The Docker image installs FFmpeg, Deno, and yt-dlp[default], which includes yt-dlp's JavaScript challenge-solver package. For YouTube searches, FRIDAY resolves metadata once and downloads the resolved webpage URL instead of repeating the search. Error responses include yt-dlp's stderr to make the actual extraction failure easier to diagnose.

## Known limitations

This is not a complete port of every Sanya Python command. Lyrics, playlists, database persistence, channel playback, full admin authorization settings, and accurate live progress/seek controls are not implemented yet and are not advertised as working commands.

## Third-party libraries

FRIDAY uses the open-source Gogram and Gortc libraries. Review their licenses and the upstream Sanya Music license before redistributing any derivative implementation.
