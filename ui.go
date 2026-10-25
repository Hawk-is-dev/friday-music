package main

import (
	"fmt"
	"html"
	"os"
	"strings"
	"time"

	"github.com/amarnathcjd/gogram/telegram"
	"github.com/amarnathcjd/gortc"
)

func (b *bot) startKeyboard() telegram.ReplyMarkup {
	kb := telegram.NewKeyboard()
	if b.botUsername != "" {
		kb.AddRow(telegram.Button.URL("Add to group", "https://t.me/"+b.botUsername+"?startgroup=true"))
	}
	kb.AddRow(telegram.Button.Data("Music commands", "friday:help"))
	if support := strings.TrimSpace(os.Getenv("SUPPORT_CHANNEL")); support != "" {
		kb.AddRow(telegram.Button.URL("Updates", support))
	}
	if support := strings.TrimSpace(os.Getenv("SUPPORT_CHAT")); support != "" {
		kb.AddRow(telegram.Button.URL("Support", support))
	}
	return kb.Build()
}

func (b *bot) handleStart(m *telegram.NewMessage) error {
	name := strings.TrimSpace(os.Getenv("BOT_NAME"))
	if name == "" { name = "FRIDAY" }
	caption := fmt.Sprintf("<b>%s MUSIC</b>\n\nHey, %s.\n\nA Telegram voice-chat music bot.\nPlay tracks, manage the queue, and control playback from one panel.\n\nUse /help to see available commands.", html.EscapeString(name), html.EscapeString(senderName(m)))
	if m.IsGroup() {
		caption = fmt.Sprintf("<b>FRIDAY MUSIC</b>\n\n%s is ready in <b>%s</b>.\n\nStart a voice chat, then use /play <code>song name</code> to begin.", html.EscapeString(name), html.EscapeString(chatTitle(m)))
	}
	imageURL := strings.TrimSpace(os.Getenv("START_IMG_URL"))
	if imageURL == "" { imageURL = "https://files.catbox.moe/3sbjl5.jpg" }
	_, err := b.client.SendMedia(m.ChatID(), &telegram.InputMediaPhotoExternal{URL: imageURL}, &telegram.MediaOptions{
		Caption: caption, ParseMode: "html", ReplyMarkup: b.startKeyboard(),
	})
	if err == nil { return nil }
	_, fallbackErr := b.client.SendMessage(m.ChatID(), caption, &telegram.SendOptions{
		ParseMode: "html", ReplyMarkup: b.startKeyboard(),
	})
	return fallbackErr
}

func senderName(m *telegram.NewMessage) string {
	if m.Sender != nil {
		name := strings.TrimSpace(m.Sender.FirstName + " " + m.Sender.LastName)
		if name != "" { return name }
	}
	return "there"
}

func chatTitle(m *telegram.NewMessage) string {
	if m.Chat != nil && strings.TrimSpace(m.Chat.Title) != "" { return m.Chat.Title }
	return "this group"
}

func (b *bot) handleHelp(m *telegram.NewMessage) error {
	text := "✦ <b>FRIDAY · MUSIC COMMANDS</b>\n━━━━━━━━━━━━━━\n♫ <b>PLAYBACK</b>\n├ /play &lt;song or URL&gt; — play audio\n├ /vplay &lt;URL or reply&gt; — play video\n├ /vp9play — VP9 video mode\n├ /playing — current track\n└ /queue — upcoming tracks\n\n◈ <b>CONTROLS</b>\n├ /pause · /resume · /skip\n├ /stop · /end · /leave\n├ /loop · /loopqueue\n├ /shuffle · /remove &lt;number&gt; · /clear\n├ /volume &lt;0–200&gt;\n└ /mute · /unmute\n\n⌁ <b>INFO</b>\n├ /stats — stream status\n└ /participants — voice chat members\n\n⚙ <b>SETUP</b>\n└ /gensession — owner-only, private chat\n━━━━━━━━━━━━━━"
	_, err := m.Reply(text, &telegram.SendOptions{
		ParseMode: "html",
		ReplyMarkup: telegram.NewKeyboard().AddRow(
			telegram.Button.Data("Home", "friday:home"),
		).Build(),
	})
	return err
}

func (b *bot) playerKeyboard(chatID int64) telegram.ReplyMarkup {
	s := b.mgr.get(chatID)
	s.mu.Lock()
	player := s.player
	var current *track
	if s.current != nil {
		copyTrack := *s.current
		current = &copyTrack
	}
	paused := player != nil && player.Paused()
	loop := s.loop
	s.mu.Unlock()

	kb := telegram.NewKeyboard()
	if player != nil && current != nil {
		position := player.Position()
		duration := player.Duration()
		if duration <= 0 && current.duration > 0 {
			duration = time.Duration(current.duration * float64(time.Second))
		}
		if duration > 0 {
			if position < 0 { position = 0 }
			if position > duration { position = duration }
			filled := int(float64(position) / float64(duration) * 10)
			if filled < 0 { filled = 0 }
			if filled > 10 { filled = 10 }
			bar := strings.Repeat("▰", filled) + strings.Repeat("▱", 10-filled)
			label := fmt.Sprintf("%s %s %s", formatPlaybackTime(position), bar, formatPlaybackTime(duration))
			kb.AddRow(telegram.Button.Data(label, "friday:timer"))
		}
	}
	pauseText, pauseData := "Ⅱ ᴘᴀᴜsᴇ", "friday:pause"
	if paused { pauseText, pauseData = "▷ ʀᴇsᴜᴍᴇ", "friday:resume" }
	loopText := "↻ ʟᴏᴏᴘ"
	if loop { loopText = "↻ ʟᴏᴏᴘ ✓" }
	kb.AddRow(
		telegram.Button.Data(pauseText, pauseData),
		telegram.Button.Data(loopText, "friday:loop"),
		telegram.Button.Data("‣‣I sᴋɪᴘ", "friday:skip"),
		telegram.Button.Data("▢ sᴛᴏᴘ", "friday:stop"),
	)
	kb.AddRow(
		telegram.Button.Data("≡ ǫᴜᴇᴜᴇ", "friday:queue"),
		telegram.Button.Data("⌯ ʜᴇʟᴘ", "friday:help"),
	)
	return kb.Build()
}

func formatPlaybackTime(value time.Duration) string {
	if value < 0 { value = 0 }
	seconds := int(value.Seconds())
	return fmt.Sprintf("%02d:%02d", seconds/60, seconds%60)
}

func (b *bot) onTrackStarted(chatID int64, t track, player *gortc.Player) {
	b.publishNowPlaying(chatID, t)
	if player == nil { return }
	s := b.mgr.find(chatID)
	if s == nil { return }
	go func() {
		ticker := time.NewTicker(10 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			s.mu.Lock()
			active := s.player == player && s.current != nil
			s.mu.Unlock()
			if !active { return }
			b.refreshNowPlaying(chatID)
		}
	}()
}

func (b *bot) trackCaption(t track, paused bool) string {
	name := strings.TrimSpace(os.Getenv("BOT_NAME"))
	if name == "" { name = "FRIDAY" }
	state := "NOW PLAYING"
	if paused { state = "PAUSED" }
	mode := "Audio"
	if t.video { mode = "Video" }
	durationText := "Live / unknown"
	if t.duration > 0 {
		seconds := int(t.duration)
		durationText = fmt.Sprintf("%02d:%02d", seconds/60, seconds%60)
	}
	caption := fmt.Sprintf("<b>%s MUSIC</b>\n\n<b>%s</b>\n%s · %s\n", html.EscapeString(name), html.EscapeString(t.title), state, mode)
	if t.uploader != "" { caption += "Channel: " + html.EscapeString(t.uploader) + "\n" }
	caption += "Duration: " + durationText + "\n"
	if t.requestedBy != "" {
		if t.requestedByID != 0 {
			caption += "Requested by: <a href=\"tg://user?id=" + fmt.Sprint(t.requestedByID) + "\">" + html.EscapeString(t.requestedBy) + "</a>\n"
		} else {
			caption += "Requested by: " + html.EscapeString(t.requestedBy) + "\n"
		}
	}
	if t.url != "" { caption += "<a href=\"" + html.EscapeString(t.url) + "\">Open source</a>\n" }
	caption += "\n— <b>" + html.EscapeString(name) + "</b>"
	return caption
}

func (b *bot) publishNowPlaying(chatID int64, t track) {
	s := b.mgr.get(chatID)
	_, _, paused := s.snapshot()
	caption := b.trackCaption(t, paused)
	markup := b.playerKeyboard(chatID)

	b.displayMu.Lock()
	messageID := b.displayMessages[chatID]
	b.displayMu.Unlock()
	if messageID != 0 {
		_, err := b.client.EditMessage(chatID, messageID, caption, &telegram.SendOptions{ParseMode: "html", ReplyMarkup: markup})
		if err == nil { return }
	}
	var sent *telegram.NewMessage
	var err error
	if t.thumbnail != "" {
		sent, err = b.client.SendMedia(chatID, &telegram.InputMediaPhotoExternal{URL: t.thumbnail}, &telegram.MediaOptions{
			Caption: caption, ParseMode: "html", ReplyMarkup: markup,
		})
	}
	if err != nil || sent == nil {
		sent, err = b.client.SendMessage(chatID, caption, &telegram.SendOptions{ParseMode: "html", ReplyMarkup: markup})
	}
	if err == nil && sent != nil {
		b.displayMu.Lock()
		b.displayMessages[chatID] = sent.ID
		b.displayMu.Unlock()
	}
}

func (b *bot) refreshNowPlaying(chatID int64) {
	t, ok, _ := b.mgr.get(chatID).snapshot()
	if !ok { return }
	b.publishNowPlaying(chatID, t)
}

func (b *bot) markPlaybackEnded(chatID int64, text string) {
	b.displayMu.Lock()
	id := b.displayMessages[chatID]
	b.displayMu.Unlock()
	if id == 0 { return }
	markup := telegram.NewKeyboard().AddRow(telegram.Button.Data("⌂ ʜᴏᴍᴇ", "friday:home")).Build()
	_, _ = b.client.EditMessage(chatID, id, text, &telegram.SendOptions{ParseMode: "html", ReplyMarkup: markup})
}

func (b *bot) markTrackEnded(chatID int64) {
	b.markPlaybackEnded(chatID, "⌁ <b>sᴏɴɢ ᴇɴᴅᴇᴅ</b>\n╰─ ǫᴜᴇᴜᴇ ᴄᴏᴍᴘʟᴇᴛᴇ.")
}

func (b *bot) handleWelcome(m *telegram.NewMessage) error {
	if m == nil || !m.IsService() || m.Action == nil || b.botID == 0 { return nil }
	if added, ok := m.Action.(*telegram.MessageActionChatAddUser); ok {
		for _, userID := range added.Users {
			if userID == b.botID { return b.handleStart(m) }
		}
	}
	return nil
}

func (b *bot) handleUICallback(cb *telegram.CallbackQuery) error {
	data := strings.TrimSpace(cb.DataString())
	chatID := cb.GetChatID()
	s := b.mgr.get(chatID)
	switch strings.TrimPrefix(data, "friday:") {
	case "home":
		name := strings.TrimSpace(os.Getenv("BOT_NAME"))
		if name == "" { name = "FRIDAY" }
		_, err := cb.Edit(fmt.Sprintf("<b>%s MUSIC</b>\n\nA Telegram voice-chat music bot.\nPlay tracks, manage the queue, and control playback from one panel.\n\nUse /help to see available commands.", html.EscapeString(name)), &telegram.SendOptions{ParseMode: "html", ReplyMarkup: b.startKeyboard()})
		_, _ = cb.Answer("Home")
		return err
	case "help":
		_, err := cb.Edit("✦ <b>FRIDAY · MUSIC COMMANDS</b>\n\n/play &lt;song or URL&gt; · /vplay · /vp9play\n/pause · /resume · /skip · /stop\n/queue · /playing · /shuffle · /volume\n/loop · /loopqueue · /remove · /clear\n/mute · /unmute · /leave\n\nAssistant session setup: /gensession in private chat.", &telegram.SendOptions{ParseMode: "html", ReplyMarkup: telegram.NewKeyboard().AddRow(telegram.Button.Data("⌂ ʜᴏᴍᴇ", "friday:home")).Build()})
		_, _ = cb.Answer("Music commands")
		return err
	case "timer":
		_, _ = cb.Answer("Playback progress")
		return nil
	case "queue":
		now, has := s.nowPlaying()
		tracks := s.list()
		var out strings.Builder
		if has { fmt.Fprintf(&out, "♫ <b>ɴᴏᴡ ᴘʟᴀʏɪɴɢ</b>\n%s\n\n", html.EscapeString(now)) } else { out.WriteString("♫ ɴᴏᴛʜɪɴɢ ɪs ᴘʟᴀʏɪɴɢ\n\n") }
		if len(tracks) == 0 { out.WriteString("╰─ ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ.") } else {
			out.WriteString("✦ <b>ᴜᴘ ɴᴇxᴛ</b>\n")
			for i, item := range tracks { fmt.Fprintf(&out, "%02d · %s\n", i+1, html.EscapeString(item.title)) }
		}
		_, err := cb.Edit(out.String(), &telegram.SendOptions{ParseMode: "html", ReplyMarkup: telegram.NewKeyboard().AddRow(telegram.Button.Data("↩ ɴᴏᴡ ᴘʟᴀʏɪɴɢ", "friday:home")).Build()})
		_, _ = cb.Answer("Queue")
		return err
	case "pause":
		if !s.pause() { _, _ = cb.Answer("Nothing is playing"); return nil }
		b.refreshNowPlaying(chatID); _, _ = cb.Answer("Paused")
	case "resume":
		if !s.resume() { _, _ = cb.Answer("Nothing is paused"); return nil }
		b.refreshNowPlaying(chatID); _, _ = cb.Answer("Resumed")
	case "skip":
		if !s.skip() { _, _ = cb.Answer("Nothing to skip"); return nil }
		_, _ = cb.Answer("Skipped")
	case "loop":
		s.toggleLoop(); b.refreshNowPlaying(chatID); _, _ = cb.Answer("Repeat toggled")
	case "stop":
		s.stop(); _ = s.leave(); b.mgr.dropIfSame(chatID, s)
		b.markPlaybackEnded(chatID, "■ <b>ᴘʟᴀʏʙᴀᴄᴋ sᴛᴏᴘᴘᴇᴅ</b>\n╰─ ǫᴜᴇᴜᴇ ᴄʟᴇᴀʀᴇᴅ.")
		_, _ = cb.Answer("Stopped")
	case "shuffle":
		s.shuffle(); b.refreshNowPlaying(chatID); _, _ = cb.Answer("Queue shuffled")
	case "mute":
		_ = s.setMuted(true); b.refreshNowPlaying(chatID); _, _ = cb.Answer("Muted")
	case "unmute":
		_ = s.setMuted(false); b.refreshNowPlaying(chatID); _, _ = cb.Answer("Unmuted")
	default:
		_, _ = cb.Answer("This control is not available")
	}
	return nil
}

func (b *bot) handleMute(m *telegram.NewMessage) error {
	if err := b.mgr.get(m.ChatID()).setMuted(true); err != nil { return reply2(m, "◈ MUTE ERROR\n└ "+err.Error()) }
	b.refreshNowPlaying(m.ChatID())
	return reply2(m, "🔇 MUTED")
}

func (b *bot) handleUnmute(m *telegram.NewMessage) error {
	if err := b.mgr.get(m.ChatID()).setMuted(false); err != nil { return reply2(m, "◈ UNMUTE ERROR\n└ "+err.Error()) }
	b.refreshNowPlaying(m.ChatID())
	return reply2(m, "🔊 UNMUTED")
}
