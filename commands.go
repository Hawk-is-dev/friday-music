package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"fmt"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/amarnathcjd/gortc"
	"github.com/amarnathcjd/gogram/telegram"
)

type bot struct {
	client *telegram.Client
	assistant *telegram.Client
	mgr *manager
	logLevel gortc.Option
	downDir string
	botUsername string
	botID int64
	displayMu sync.Mutex
	displayMessages map[int64]int32
	sessionMu sync.Mutex
	sessionFlow *sessionFlow
}

func (b *bot) controlPermission(chatID, userID int64, private bool) (bool, string) {
	if private || userID == configuredOwnerID {
		return true, ""
	}
	member, err := b.client.GetChatMember(chatID, userID)
	if err != nil {
		return false, "Could not verify admin permissions. Make sure FRIDAY is an admin in this group."
	}
	if member.Status == telegram.Admin || member.Status == telegram.Creator {
		return true, ""
	}
	return false, "Only group admins can control playback."
}

func (b *bot) requireControl(m *telegram.NewMessage) error {
	allowed, reason := b.controlPermission(m.ChatID(), m.SenderID(), m.IsPrivate())
	if allowed { return nil }
	return reply2(m, "⛔ " + reason)
}

func (b *bot) allowCallbackControl(cb *telegram.CallbackQuery) bool {
	allowed, reason := b.controlPermission(cb.GetChatID(), cb.GetSenderID(), cb.IsPrivate())
	if allowed { return true }
	_, _ = cb.Answer(reason)
	return false
}

func (b *bot) callFactory(vp9 bool) *gortc.Call {
	opts := []gortc.Option{b.logLevel}
	if vp9 { opts = append(opts, gortc.WithVideoCodec(gortc.MimeTypeVP9)) }
	return gortc.NewCall(b.assistant, opts...)
}

func (b *bot) handlePlay(video, vp9 bool) telegram.MessageHandler {
	return func(m *telegram.NewMessage) error {
		if b.assistant == nil {
			return reply2(m, "✦ ASSISTANT SESSION REQUIRED\n└ Open FRIDAY in private chat and run /gensession. Save the generated value as STRING_SESSION (SESSION_STRING is also accepted), then restart the service.")
		}
		status, _ := m.Reply("✦ FRIDAY MUSIC\n└ Finding your track…")
		var t track
		var err error

		handledReplyMedia := false
		if m.IsReply() {
			replied, replyErr := m.GetReplyMessage()
			if replyErr != nil {
				return edit(status, "FRIDAY MUSIC\nCouldn’t read the replied message.")
			}
			if isPlayableTelegramMedia(replied) {
				handledReplyMedia = true
				t.title = mediaTitle(replied)
				t.duration = mediaDuration(replied)
				t.path, err = replied.Download(&telegram.DownloadOptions{
					FileName: filepath.Join(b.downDir, fmt.Sprintf("%d_%d_%s", m.ChatID(), replied.ID, sanitize(t.title))),
				})
			}
		}
		if !handledReplyMedia && strings.TrimSpace(m.Args()) != "" {
			ctx, cancel := context.WithTimeout(context.Background(), 8*time.Minute)
			defer cancel()
			t, err = downloadExternal(ctx, b.downDir, strings.TrimSpace(m.Args()), video)
		} else if !handledReplyMedia {
			return edit(status, "HOW TO PLAY\n/play <song name or URL>\nReply to audio with /play\nReply to video with /vplay")
		}
		if err != nil {
			return edit(status, "✦ DOWNLOAD FAILED\n├ "+brief(err.Error(), 700)+"\n└ Check the yt-dlp extraction details above.")
		}
		t.video, t.vp9 = video, vp9
		t.requestedBy = senderName(m)
		if m.Sender != nil { t.requestedByID = m.Sender.ID }
		if t.title == "" { t.title = "Telegram media" }

		s := b.mgr.get(m.ChatID())
		s.mu.Lock()
		s.useVP9 = vp9
		needsAutoJoin := s.call == nil
		s.mu.Unlock()

		var inviteErr error
		if needsAutoJoin {
			inviteErr = b.tryAutoJoinAssistant(m.ChatID())
		}
		pos, startNow, enqueueErr := s.enqueueTrack(b.callFactory, m.ChatID(), t)
		if enqueueErr != nil {
			removeFile(t.path)
			message := "Could not join voice chat: " + brief(enqueueErr.Error(), 350) + "\nMake sure the group has an active voice chat and the bot can invite users."
			if inviteErr != nil {
				message += "\nAssistant auto-join note: " + brief(inviteErr.Error(), 250)
			}
			return edit(status, message)
		}
		if startNow {
			s.startNext()
			if status != nil { _, _ = b.client.DeleteMessages(status.ChannelID(), []int32{status.ID}) }
			return nil
		}
		return edit(status, fmt.Sprintf("♫ ADDED TO QUEUE  #%d\n╰─ %s", pos, t.title))
	}
}

func downloadExternal(ctx context.Context, dir, query string, video bool) (track, error) {
	query = strings.TrimSpace(query)
	if query == "" {
		return track{}, fmt.Errorf("enter a song name or URL")
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return track{}, fmt.Errorf("create download directory: %w", err)
	}
	cookiePath, cleanupCookies, err := prepareYtDlpCookies(dir)
	if err != nil {
		return track{}, fmt.Errorf("prepare yt-dlp cookies: %w", err)
	}
	defer cleanupCookies()
	cookieArgs := []string{}
	if cookiePath != "" {
		cookieArgs = append(cookieArgs, "--cookies", cookiePath)
	}

	target := query
	isURL := false
	if parsed, parseErr := url.ParseRequestURI(query); parseErr == nil && parsed.Scheme != "" {
		if parsed.Scheme != "https" && parsed.Scheme != "http" {
			return track{}, fmt.Errorf("only http/https URLs are supported")
		}
		isURL = true
	} else {
		target = "ytsearch1:" + query
	}

	// Retry metadata extraction with a second YouTube client strategy. This helps
	// with transient extractor changes; it cannot bypass private/blocked media.
	extractorVariants := [][]string{
		{},
		{"--extractor-args", "youtube:player_client=mweb,tv"},
	}
	var t track
	var lastErr string
	for attempt, extra := range extractorVariants {
		metaArgs := []string{
			"--ignore-config", "--no-warnings", "--no-playlist", "--skip-download", "--ignore-no-formats-error",
			"--retries", "3", "--extractor-retries", "3", "--socket-timeout", "25",
			"--js-runtimes", "deno",
			"--print", "%(id)s\\t%(title)s\\t%(duration)s\\t%(thumbnail)s\\t%(uploader)s\\t%(webpage_url)s",
		}
		metaArgs = append(metaArgs, extra...)
		metaArgs = append(metaArgs, cookieArgs...)
		metaArgs = append(metaArgs, target)
		metaCmd := exec.CommandContext(ctx, "yt-dlp", metaArgs...)
		var metaOut, metaErr bytes.Buffer
		metaCmd.Stdout, metaCmd.Stderr = &metaOut, &metaErr
		if runErr := metaCmd.Run(); runErr == nil {
			t, err = parseYtDlpInfo(metaOut.String(), query)
			if err == nil {
				break
			}
			lastErr = err.Error()
		} else {
			lastErr = strings.TrimSpace(metaErr.String())
			if lastErr == "" {
				lastErr = runErr.Error()
			}
		}
		if attempt == len(extractorVariants)-1 {
			return track{}, fmt.Errorf("yt-dlp metadata lookup failed after retries: %s", brief(lastErr, 700))
		}
		if ctx.Err() != nil {
			return track{}, ctx.Err()
		}
	}
	if t.title == "" || t.url == "" {
		return track{}, fmt.Errorf("yt-dlp could not resolve a usable track: %s", brief(lastErr, 500))
	}
	if t.duration > float64(maxDurationMinutes()*60) {
		return track{}, fmt.Errorf("track is %.0f minutes long; FRIDAY's limit is %d minutes", t.duration/60, maxDurationMinutes())
	}

	base := filepath.Join(dir, fmt.Sprintf("%s_%d", sanitize(t.id), time.Now().UnixNano()))
	common := []string{
		"--ignore-config", "--no-warnings", "--no-playlist", "--force-overwrites",
		"--retries", "5", "--fragment-retries", "5", "--extractor-retries", "3",
		"--socket-timeout", "25", "--js-runtimes", "deno",
	}
	// Try normal extraction first, then alternate client/format strategies.
	// yt-dlp/FFmpeg errors are retained so the user gets a useful failure reason.
	type downloadAttempt struct {
		label string
		args  []string
	}
	var attempts []downloadAttempt
	if video {
		attempts = []downloadAttempt{
			{"mp4-compatible", []string{"-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "--merge-output-format", "mp4"}},
			{"alternate-format", []string{"--extractor-args", "youtube:player_client=mweb,tv", "-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"}},
			{"single-file-fallback", []string{"-f", "best", "--extractor-args", "youtube:player_client=mweb,tv"}},
		}
	} else {
		attempts = []downloadAttempt{
			{"best-audio-mp3", []string{"-f", "bestaudio/best", "-x", "--audio-format", "mp3", "--audio-quality", "0"}},
			{"alternate-client-mp3", []string{"--extractor-args", "youtube:player_client=mweb,tv", "-f", "bestaudio/best", "-x", "--audio-format", "mp3", "--audio-quality", "0"}},
			{"best-format-fallback", []string{"-f", "best", "-x", "--audio-format", "mp3", "--audio-quality", "0"}},
		}
	}
	var downloadErr string
	for i, attempt := range attempts {
		args := append([]string{}, common...)
		args = append(args, attempt.args...)
		args = append(args, cookieArgs...)
		args = append(args, "-o", base+".%(ext)s", "--print", "after_move:filepath", t.url)
		cmd := exec.CommandContext(ctx, "yt-dlp", args...)
		var out, stderr bytes.Buffer
		cmd.Stdout, cmd.Stderr = &out, &stderr
		if runErr := cmd.Run(); runErr == nil {
			lines := strings.Split(strings.TrimSpace(out.String()), "\\n")
			if len(lines) > 0 && strings.TrimSpace(lines[len(lines)-1]) != "" {
				candidate := strings.TrimSpace(lines[len(lines)-1])
				info, statErr := os.Stat(candidate)
				if statErr == nil && info.Size() > 0 {
					t.path = candidate
					t.requested = query
					t.video = video
					return t, nil
				}
				downloadErr = "yt-dlp returned a path but the file is missing or empty"
			} else {
				downloadErr = "yt-dlp completed without returning the output file path"
			}
		} else {
			downloadErr = strings.TrimSpace(stderr.String())
			if downloadErr == "" {
				downloadErr = strings.TrimSpace(out.String())
			}
			if downloadErr == "" {
				downloadErr = runErr.Error()
			}
		}
		for _, partial := range mustGlob(base + ".*") {
			removeFile(partial)
		}
		if ctx.Err() != nil {
			return track{}, ctx.Err()
		}
		if i < len(attempts)-1 {
			continue
		}
	}
	sourceType := "search"
	if isURL {
		sourceType = "URL"
	}
	return track{}, fmt.Errorf("all %d download strategies failed for this %s: %s", len(attempts), sourceType, brief(downloadErr, 700))
}

func parseYtDlpInfo(output, requested string) (track, error) {
	line := strings.TrimSpace(strings.SplitN(output, "\n", 2)[0])
	if line == "" { return track{}, fmt.Errorf("yt-dlp returned no metadata") }
	fields := strings.Split(line, "\t")
	if len(fields) < 6 { return track{}, fmt.Errorf("yt-dlp returned incomplete metadata (%d fields)", len(fields)) }
	t := track{
		id: strings.TrimSpace(fields[0]), title: strings.TrimSpace(fields[1]),
		thumbnail: strings.TrimSpace(fields[3]), uploader: strings.TrimSpace(fields[4]),
		url: strings.TrimSpace(fields[5]), requested: requested,
	}
	if strings.EqualFold(t.thumbnail, "NA") { t.thumbnail = "" }
	if strings.EqualFold(t.uploader, "NA") { t.uploader = "" }
	if strings.EqualFold(t.url, "NA") { t.url = "" }
	if strings.TrimSpace(fields[2]) != "" && !strings.EqualFold(strings.TrimSpace(fields[2]), "NA") {
		t.duration, _ = strconv.ParseFloat(strings.TrimSpace(fields[2]), 64)
	}
	if t.url == "" && strings.HasPrefix(requested, "http") { t.url = requested }
	if t.title == "" { t.title = t.id }
	if t.id == "" { t.id = sanitize(t.title) }
	if t.title == "" || t.url == "" { return track{}, fmt.Errorf("yt-dlp returned no usable title or webpage URL") }
	return t, nil
}

func parseYtDlpMetadata(output string) (string, string, error) {
	lines := strings.Split(strings.TrimSpace(output), "\n")
	if len(lines) < 2 || strings.TrimSpace(lines[0]) == "" || strings.TrimSpace(lines[1]) == "" {
		return "", "", fmt.Errorf("yt-dlp returned incomplete metadata")
	}
	return strings.TrimSpace(lines[0]), strings.TrimSpace(lines[1]), nil
}

func parseYtDlpDuration(output string) (float64, bool) {
	lines := strings.Split(strings.TrimSpace(output), "\n")
	if len(lines) < 3 { return 0, false }
	value := strings.TrimSpace(lines[2])
	if value == "" || strings.EqualFold(value, "NA") { return 0, false }
	duration, err := strconv.ParseFloat(value, 64)
	return duration, err == nil && duration >= 0
}

func maxDurationMinutes() int {
	// Match Sanya's DURATION_LIMIT variable name; retain the earlier
	// MAX_DURATION_MINUTES name as a backwards-compatible fallback.
	raw := strings.TrimSpace(os.Getenv("DURATION_LIMIT"))
	if raw == "" { raw = strings.TrimSpace(os.Getenv("MAX_DURATION_MINUTES")) }
	limit, err := strconv.Atoi(raw)
	if err != nil || limit < 1 || limit > 240 {
		return 30
	}
	return limit
}

func prepareYtDlpCookies(dir string) (string, func(), error) {
	// Prefer raw cookie text so Railway users do not need to Base64-encode it.
	// This also lets COOKIES_TEXT take precedence over a stale COOKIES_PATH value.
	if raw := strings.TrimSpace(os.Getenv("COOKIES_TEXT")); raw != "" {
		return writeTemporaryCookies(dir, []byte(raw))
	}
	if path := strings.TrimSpace(os.Getenv("COOKIES_PATH")); path != "" {
		if info, err := os.Stat(path); err != nil {
			return "", func() {}, fmt.Errorf("COOKIES_PATH is not readable: %w", err)
		} else if !info.Mode().IsRegular() {
			return "", func() {}, fmt.Errorf("COOKIES_PATH must point to a regular file")
		}
		file, err := os.Open(path)
		if err != nil {
			return "", func() {}, fmt.Errorf("COOKIES_PATH is not readable: %w", err)
		}
		_ = file.Close()
		return path, func() {}, nil
	}
	encoded := strings.TrimSpace(os.Getenv("COOKIES_B64"))
	if encoded == "" {
		return "", func() {}, nil
	}
	data, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		data, err = base64.RawStdEncoding.DecodeString(encoded)
	}
	if err != nil {
		return "", func() {}, fmt.Errorf("COOKIES_B64 must be standard base64: %w", err)
	}
	return writeTemporaryCookies(dir, data)
}

func writeTemporaryCookies(dir string, data []byte) (string, func(), error) {
	if len(bytes.TrimSpace(data)) == 0 {
		return "", func() {}, fmt.Errorf("cookie content is empty")
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", func() {}, fmt.Errorf("create cookie directory: %w", err)
	}
	file, err := os.CreateTemp(dir, "friday-cookies-*.txt")
	if err != nil {
		return "", func() {}, err
	}
	path := file.Name()
	cleanup := func() { _ = os.Remove(path) }
	if _, err := file.Write(data); err != nil {
		_ = file.Close()
		cleanup()
		return "", func() {}, err
	}
	if len(data) > 0 && data[len(data)-1] != '\n' {
		if _, err := file.Write([]byte("\n")); err != nil {
			_ = file.Close()
			cleanup()
			return "", func() {}, err
		}
	}
	if err := file.Close(); err != nil {
		cleanup()
		return "", func() {}, err
	}
	return path, cleanup, nil
}

func (b *bot) register() {
	b.client.OnCommand("gensession", b.startSessionGeneration)
	b.client.OnCommand("sessionphone", b.handleSessionPhone)
	b.client.OnCommand("sessioncode", b.handleSessionCode)
	b.client.OnCommand("sessionpassword", b.handleSessionPassword)
	b.client.OnCommand("start", b.handleStart)
	b.client.OnCommand("help", b.handleHelp)
	b.client.OnCallback("^friday:", b.handleUICallback)
	b.client.On("message", b.handleWelcome)
	b.client.OnCommand("play", b.handlePlay(false, false))
	b.client.OnCommand("vplay", b.handlePlay(true, false))
	b.client.OnCommand("vp9play", b.handlePlay(true, true))
	b.client.OnCommand("skip", b.handleSkip)
	b.client.OnCommand("pause", b.handlePause)
	b.client.OnCommand("resume", b.handleResume)
	b.client.OnCommand("stop", b.handleStop)
	b.client.OnCommand("end", b.handleStop)
	b.client.OnCommand("leave", b.handleLeave)
	b.client.OnCommand("volume", b.handleVolume)
	b.client.OnCommand("mute", b.handleMute)
	b.client.OnCommand("unmute", b.handleUnmute)
	b.client.OnCommand("queue", b.handleQueue)
	b.client.OnCommand("loop", b.handleLoop)
	b.client.OnCommand("loopqueue", b.handleLoopQueue)
	b.client.OnCommand("remove", b.handleRemove)
	b.client.OnCommand("clear", b.handleClear)
	b.client.OnCommand("shuffle", b.handleShuffle)
	b.client.OnCommand("playing", b.handlePlaying)
	b.client.OnCommand("stats", b.handleStats)
	b.client.OnCommand("participants", b.handleParticipants)
}
func (b *bot) handleSkip(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	if !b.mgr.get(m.ChatID()).skip() { return reply2(m, "♫ NOTHING PLAYING\n╰─ Queue a track with /play.") }
	return reply2(m, "⏭ TRACK SKIPPED")
}
func (b *bot) handlePause(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	if !b.mgr.get(m.ChatID()).pause() { return reply2(m, "Ⅱ Nothing is playing to pause.") }
	b.refreshNowPlaying(m.ChatID())
	return reply2(m, "Ⅱ PLAYBACK PAUSED")
}
func (b *bot) handleResume(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	if !b.mgr.get(m.ChatID()).resume() { return reply2(m, "▶ Nothing is paused right now.") }
	b.refreshNowPlaying(m.ChatID())
	return reply2(m, "▶ PLAYBACK RESUMED")
}
func (b *bot) handleStop(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	s := b.mgr.get(m.ChatID())
	s.stop()
	err := s.leave()
	b.mgr.dropIfSame(m.ChatID(), s)
	b.markPlaybackEnded(m.ChatID(), "■ <b>ᴘʟᴀʏʙᴀᴄᴋ sᴛᴏᴘᴘᴇᴅ</b>\n╰─ ǫᴜᴇᴜᴇ ᴄʟᴇᴀʀᴇᴅ.")
	if err != nil { return reply2(m, "■ STOPPED\n└ Voice-chat warning: "+err.Error()) }
	return reply2(m, "■ PLAYBACK STOPPED\n╰─ Queue cleared.")
}
func (b *bot) handleLeave(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	s := b.mgr.get(m.ChatID())
	err := s.leave()
	b.mgr.dropIfSame(m.ChatID(), s)
	if err != nil { return reply2(m, "↗ Left with warning: "+err.Error()) }
	return reply2(m, "↗ LEFT VOICE CHAT")
}
func (b *bot) handleVolume(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	v, err := strconv.Atoi(strings.TrimSpace(m.Args()))
	if err != nil || v < 0 || v > 200 { return reply2(m, "◈ Usage: /volume <0-200>") }
	if err := b.mgr.get(m.ChatID()).setVolume(v); err != nil { return reply2(m, "◈ VOLUME ERROR\n└ "+err.Error()) }
	b.refreshNowPlaying(m.ChatID())
	return reply2(m, fmt.Sprintf("◈ VOLUME SET\n╰─ %d%%", v))
}
func (b *bot) handleQueue(m *telegram.NewMessage) error {
	s := b.mgr.get(m.ChatID()); now, ok := s.nowPlaying(); tracks := s.list()
	var out strings.Builder
	if ok { out.WriteString("♫ NOW PLAYING\n╰─ "+now+"\n\n") } else { out.WriteString("♫ NOTHING PLAYING\n\n") }
	if s.loopEnabled() { out.WriteString("↻ Repeat: current track\n") }
	if s.loopQueueEnabled() { out.WriteString("↻ Repeat: queue\n") }
	if len(tracks) == 0 { out.WriteString("╰─ Queue is empty.") } else {
		out.WriteString("✦ UP NEXT\n")
		for i, t := range tracks { fmt.Fprintf(&out, "%02d  ·  %s\n", i+1, t.title) }
	}
	return reply2(m, out.String())
}
func (b *bot) handleLoop(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	enabled := b.mgr.get(m.ChatID()).toggleLoop()
	if enabled {
		b.refreshNowPlaying(m.ChatID())
	return reply2(m, "↻ REPEAT ENABLED\n╰─ The current track will repeat until /loop is used again.")
	}
	b.refreshNowPlaying(m.ChatID())
	return reply2(m, "↻ REPEAT DISABLED")
}

func (b *bot) handleLoopQueue(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	enabled := b.mgr.get(m.ChatID()).toggleLoopQueue()
	if enabled {
		return reply2(m, "↻ QUEUE REPEAT ENABLED\n╰─ Tracks will cycle in queue order.")
	}
	return reply2(m, "↻ QUEUE REPEAT DISABLED")
}

func (b *bot) handleClear(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	count := b.mgr.get(m.ChatID()).clearQueue()
	return reply2(m, fmt.Sprintf("⌫ QUEUE CLEARED\n╰─ Removed %d upcoming track(s).", count))
}

func (b *bot) handleRemove(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	index, err := strconv.Atoi(strings.TrimSpace(m.Args()))
	if err != nil || index < 1 {
		return reply2(m, "⌫ Usage: /remove <queue number>")
	}
	s := b.mgr.get(m.ChatID())
	removed, ok := s.removeQueued(index)
	if !ok {
		return reply2(m, "⌫ That queue position does not exist. Check /queue.")
	}
	removeFile(removed.path)
	return reply2(m, "⌫ REMOVED FROM QUEUE\n╰─ "+removed.title)
}

func (b *bot) handlePlaying(m *telegram.NewMessage) error {
	title, ok := b.mgr.get(m.ChatID()).nowPlaying()
	if !ok { return reply2(m, "♫ NOTHING PLAYING\n╰─ Queue a track with /play.") }
	return reply2(m, "♫ NOW PLAYING\n╰─ "+title)
}
func (b *bot) handleStats(m *telegram.NewMessage) error {
	s := b.mgr.get(m.ChatID()); s.mu.Lock(); bwe, call, vp9 := s.lastBwe, s.call, s.useVP9; s.mu.Unlock()
	state := "not in voice chat"; if call != nil { state = call.State() }
	codec := "VP8"; if vp9 { codec = "VP9" }
	return reply2(m, fmt.Sprintf("⌁ FRIDAY · STREAM STATUS\n━━━━━━━━━━━━━━\n◈ State     %s\n◈ Codec     %s\n◈ Bitrate   %d kbps\n◈ Loss      %d/255\n◈ Jitter    %d\n━━━━━━━━━━━━━━", state, codec, bwe.BitrateBps/1000, bwe.FractionLost, bwe.Jitter))
}
func (b *bot) handleParticipants(m *telegram.NewMessage) error {
	s := b.mgr.get(m.ChatID()); s.mu.Lock(); call := s.call; s.mu.Unlock()
	if call == nil { return reply2(m, "⌁ FRIDAY ISN’T IN A VOICE CHAT") }
	parts := call.Participants(); if len(parts) == 0 { return reply2(m, "⌁ No participants reported yet.") }
	var out strings.Builder; fmt.Fprintf(&out, "⌁ VOICE CHAT · %d MEMBERS\n", len(parts))
	for _, p := range parts { fmt.Fprintf(&out, "├ ID %d · muted %v · video %v · volume %d\n", p.PeerID, p.Muted, p.HasVideo, p.Volume) }
	return reply2(m, out.String())
}
func reply2(m *telegram.NewMessage, text string) error { _, err := m.Reply(text); return err }
func edit(m *telegram.NewMessage, text string) error { if m == nil { return nil }; _, err := m.Edit(text); return err }
func isPlayableTelegramMedia(m *telegram.NewMessage) bool {
	return m != nil && (m.Audio() != nil || m.Voice() != nil || m.Video() != nil)
}

func mediaTitle(m *telegram.NewMessage) string {
	if m == nil { return "telegram-media" }
	docs := []*telegram.DocumentObj{m.Audio(), m.Voice(), m.Video()}
	for _, doc := range docs {
		if doc == nil { continue }
		for _, attr := range doc.Attributes {
			if audio, ok := attr.(*telegram.DocumentAttributeAudio); ok && audio.Title != "" {
				if audio.Performer != "" { return audio.Performer + " - " + audio.Title }
				return audio.Title
			}
			if filename, ok := attr.(*telegram.DocumentAttributeFilename); ok && filename.FileName != "" {
				return filename.FileName
			}
		}
	}
	return "Telegram media"
}

func mediaDuration(m *telegram.NewMessage) float64 {
	if m == nil { return 0 }
	docs := []*telegram.DocumentObj{m.Audio(), m.Voice(), m.Video()}
	for _, doc := range docs {
		if doc == nil { continue }
		for _, attr := range doc.Attributes {
			switch value := attr.(type) {
			case *telegram.DocumentAttributeAudio:
				if value.Duration > 0 { return float64(value.Duration) }
			case *telegram.DocumentAttributeVideo:
				if value.Duration > 0 { return float64(value.Duration) }
			}
		}
	}
	return 0
}
func brief(s string, limit int) string {
	s = strings.Join(strings.Fields(s), " ")
	if limit > 0 && len(s) > limit {
		return s[:limit] + "…"
	}
	return s
}

func mustGlob(pattern string) []string {
	matches, _ := filepath.Glob(pattern)
	return matches
}

func sanitize(name string) string {
	return strings.NewReplacer("/", "_", "\\", "_", ":", "_", "*", "_", "?", "_", "\"", "_", "<", "_", ">", "_", "|", "_", " ", "_").Replace(name)
}

func (b *bot) handleShuffle(m *telegram.NewMessage) error {
	if err := b.requireControl(m); err != nil { return err }
	count := b.mgr.get(m.ChatID()).shuffle()
	if count < 2 { return reply2(m, "⤨ Add at least two upcoming tracks to shuffle.") }
	return reply2(m, fmt.Sprintf("⤨ QUEUE SHUFFLED\n╰─ Mixed %d upcoming tracks.", count))
}
