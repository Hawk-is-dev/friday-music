# FRIDAY Music

FRIDAY is a Go-based Telegram voice-chat music bot built with Gogram and Gortc. It uses FFmpeg, yt-dlp, and Deno for media extraction and audio processing.

## Music features

- /play <song name or URL> — play audio; can also reply to Telegram audio/media
- /vplay <URL or reply> and /vp9play <URL or reply> — video playback
- /pause, /resume, /skip, /stop, /end, /leave
- /queue, /playing, /shuffle, /volume 0-200
- /loop, /loopqueue, /remove <number>, /clear
- /mute, /unmute (playback controls are group-admin-only; the configured owner can also control playback)
- /stats, /participants
- /start, /help
- /gensession — owner-only assistant-session setup in private chat

Playback is isolated per group. The now-playing card uses the source thumbnail when available, shows requester and track metadata, updates a playback progress bar every 10 seconds, and provides inline pause/resume, repeat, skip, stop, queue, and help controls. The start panel supports an add-to-group button and optional support links.

## Railway variables

Required:
- BOT_TOKEN — token from BotFather
- API_ID and API_HASH — from my.telegram.org
- STRING_SESSION — assistant user session for voice-chat playback (same variable name used by Sanya). SESSION_STRING is accepted as a compatibility alias. Important: the variable name matches Sanya, but Sanya's Pyrogram session string is not compatible with Gogram; generate a FRIDAY/Gogram string using /gensession.

Optional:
- BOT_NAME — display name, default FRIDAY
- START_IMG_URL — welcome image URL (same variable name used by Sanya)
- SUPPORT_CHANNEL and SUPPORT_CHAT — links shown on the start panel; accepts @username or a full URL. Defaults: @eternalsportal and @genzportals
- COOKIES_B64 or COOKIES_PATH — optional YouTube cookies, if required
- DOWNLOAD_DIR — defaults to downloads
- LOG_LEVEL — defaults to info
- DURATION_LIMIT — track duration limit in minutes, defaults to 30, accepted range 1–240. The older MAX_DURATION_MINUTES name remains supported as a fallback.

Playback controls are restricted to group admins, with the configured owner allowed as an override. FRIDAY checks admin status through Telegram before executing those commands. The owner ID used by /gensession is configured in code, so you do not need an OWNER_ID variable. Sanya also defines MONGO_DB_URI, REDIS_URL, REDIS_TOKEN, LOGGER_ID, POST_CHANNEL_ID, GROQ_API_KEY, GROQ_MODEL, API_KEY, API_URL, VERCEL_SEARCH_URL, LASTFM_API_KEY, and STRING_SESSION2 through STRING_SESSION7. FRIDAY does not currently use these: database persistence, AI tools, logging-channel features, and multiple assistant accounts have not been ported, so adding those variables alone will not enable them.

## Setup

1. Set the required Railway variables.
2. Start FRIDAY and open its private chat as the configured owner.
3. Run /gensession, then follow /sessionphone, /sessioncode, and /sessionpassword prompts if two-step verification is enabled.
4. Copy the generated Gogram value to STRING_SESSION and restart the service. Do not paste a session exported by Sanya/Pyrogram; the libraries use different session formats.
5. Add the bot to a group, make it an admin with permission to invite users, and start a voice chat before playing music.

## Media extraction

The Docker image installs FFmpeg, Deno, and yt-dlp[default], which includes yt-dlp's JavaScript challenge-solver package. For YouTube searches, FRIDAY resolves metadata once and downloads the resolved webpage URL instead of repeating the search. Error responses include yt-dlp's stderr to make the actual extraction failure easier to diagnose.

## Known limitations

This is not a complete port of every Sanya Python command. Lyrics, playlists, database persistence, channel playback, full admin authorization settings, and accurate live progress/seek controls are not implemented yet and are not advertised as working commands.

## Third-party libraries

FRIDAY uses the open-source Gogram and Gortc libraries. Review their licenses and the upstream Sanya Music license before redistributing any derivative implementation.
