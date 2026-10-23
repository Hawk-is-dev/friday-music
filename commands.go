package main

import (
	"fmt"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/amarnathcjd/gortc"
	"github.com/amarnathcjd/gogram/telegram"
)

type bot struct {
	client *telegram.Client
	assistant *telegram.Client
	mgr *manager
	logLevel gortc.Option
	downDir string
}

func (b *bot) callFactory(vp9 bool) *gortc.Call {
	opts := []gortc.Option{b.logLevel}
	if vp9 { opts = append(opts, gortc.WithVideoCodec(gortc.MimeTypeVP9)) }
	return gortc.NewCall(b.assistant, opts...)
}

func (b *bot) handlePlay(video, vp9 bool) telegram.MessageHandler {
	return func(m *telegram.NewMessage) error {
		if !m.IsReply() { return reply2(m, "Reply to a Telegram audio/video file with /play or /vplay.") }
		reply, err := m.GetReplyMessage()
		if err != nil { return reply2(m, "Could not read the replied message.") }
		if !reply.IsMedia() { return reply2(m, "The replied message has no downloadable media.") }
		status, _ := m.Reply("FRIDAY: downloading media…")
		title := mediaTitle(reply)
		dst := filepath.Join(b.downDir, fmt.Sprintf("%d_%d_%s", m.ChatID(), reply.ID, sanitize(title)))
		path, err := reply.Download(&telegram.DownloadOptions{FileName:dst})
		if err != nil { return edit(status, "Download failed: "+err.Error()) }
		s := b.mgr.get(m.ChatID())
		s.mu.Lock(); s.useVP9 = vp9; s.mu.Unlock()
		if err := s.ensureCall(b.callFactory, m.ChatID()); err != nil {
			removeFile(path); return edit(status, "Could not join voice chat: "+err.Error()+"\nStart a voice chat first and ensure the assistant account is in the group.")
		}
		pos, startNow := s.enqueue(track{title:title, path:path, video:video, vp9:vp9})
		if startNow { s.startNext(); return edit(status, "Now playing: "+title) }
		return edit(status, fmt.Sprintf("Added to queue #%d: %s", pos, title))
	}
}
func (b *bot) register() {
	b.client.OnCommand("start", func(m *telegram.NewMessage) error { return reply2(m, "FRIDAY Music is online. Use /help to see commands.") })
	b.client.OnCommand("help", func(m *telegram.NewMessage) error { return reply2(m, "FRIDAY MUSIC\n/play — play replied Telegram audio\n/vplay — play replied video\n/pause — pause\n/resume — resume\n/skip — skip track\n/stop — clear queue and stop\n/leave — leave voice chat\n/queue — show queue\n/playing — current track\n/volume 0-200 — set volume\n/stats — stream stats\n/participants — voice chat participants") })
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
	b.client.OnCommand("queue", b.handleQueue)
	b.client.OnCommand("playing", b.handlePlaying)
	b.client.OnCommand("stats", b.handleStats)
	b.client.OnCommand("participants", b.handleParticipants)
}
func (b *bot) handleSkip(m *telegram.NewMessage) error {
	if !b.mgr.get(m.ChatID()).skip() { return reply2(m, "Nothing is playing.") }
	return reply2(m, "Skipped.")
}
func (b *bot) handlePause(m *telegram.NewMessage) error {
	if !b.mgr.get(m.ChatID()).pause() { return reply2(m, "Nothing to pause.") }
	return reply2(m, "Paused.")
}
func (b *bot) handleResume(m *telegram.NewMessage) error {
	if !b.mgr.get(m.ChatID()).resume() { return reply2(m, "Nothing to resume.") }
	return reply2(m, "Resumed.")
}
func (b *bot) handleStop(m *telegram.NewMessage) error {
	s := b.mgr.get(m.ChatID()); s.stop()
	if err := s.leave(); err != nil { return reply2(m, "Stopped; voice-chat leave warning: "+err.Error()) }
	b.mgr.drop(m.ChatID())
	return reply2(m, "Stopped and queue cleared.")
}
func (b *bot) handleLeave(m *telegram.NewMessage) error {
	s := b.mgr.get(m.ChatID())
	if err := s.leave(); err != nil { return reply2(m, "Leave failed: "+err.Error()) }
	b.mgr.drop(m.ChatID()); return reply2(m, "Left the voice chat.")
}
func (b *bot) handleVolume(m *telegram.NewMessage) error {
	v, err := strconv.Atoi(strings.TrimSpace(m.Args()))
	if err != nil || v < 0 || v > 200 { return reply2(m, "Usage: /volume <0-200>") }
	if err := b.mgr.get(m.ChatID()).setVolume(v); err != nil { return reply2(m, "Volume error: "+err.Error()) }
	return reply2(m, fmt.Sprintf("Volume set to %d%%.", v))
}
func (b *bot) handleQueue(m *telegram.NewMessage) error {
	s := b.mgr.get(m.ChatID()); now, ok := s.nowPlaying(); tracks := s.list()
	var out strings.Builder
	if ok { out.WriteString("Now playing: "+now+"\n") } else { out.WriteString("Nothing playing.\n") }
	if len(tracks) == 0 { out.WriteString("Queue is empty.") } else {
		out.WriteString("Up next:\n")
		for i, t := range tracks { fmt.Fprintf(&out, "%d. %s\n", i+1, t.title) }
	}
	return reply2(m, out.String())
}
func (b *bot) handlePlaying(m *telegram.NewMessage) error {
	title, ok := b.mgr.get(m.ChatID()).nowPlaying()
	if !ok { return reply2(m, "Nothing is playing.") }
	return reply2(m, "Now playing: "+title)
}
func (b *bot) handleStats(m *telegram.NewMessage) error {
	s := b.mgr.get(m.ChatID()); s.mu.Lock(); bwe, call, vp9 := s.lastBwe, s.call, s.useVP9; s.mu.Unlock()
	state := "not in voice chat"; if call != nil { state = call.State() }
	codec := "VP8"; if vp9 { codec = "VP9" }
	return reply2(m, fmt.Sprintf("State: %s\nCodec: %s\nBitrate: %d kbps\nPacket loss: %d/255\nJitter: %d", state, codec, bwe.BitrateBps/1000, bwe.FractionLost, bwe.Jitter))
}
func (b *bot) handleParticipants(m *telegram.NewMessage) error {
	s := b.mgr.get(m.ChatID()); s.mu.Lock(); call := s.call; s.mu.Unlock()
	if call == nil { return reply2(m, "Not in a voice chat.") }
	parts := call.Participants(); if len(parts) == 0 { return reply2(m, "No participants reported yet.") }
	var out strings.Builder; fmt.Fprintf(&out, "%d participant(s):\n", len(parts))
	for _, p := range parts { fmt.Fprintf(&out, "• peer=%d muted=%v video=%v volume=%d\n", p.PeerID, p.Muted, p.HasVideo, p.Volume) }
	return reply2(m, out.String())
}
func reply2(m *telegram.NewMessage, text string) error { _, err := m.Reply(text); return err }
func edit(m *telegram.NewMessage, text string) error { if m == nil { return nil }; _, err := m.Edit(text); return err }
func mediaTitle(m *telegram.NewMessage) string {
	if a := m.Audio(); a != nil {
		for _, attr := range a.Attributes {
			if t, ok := attr.(*telegram.DocumentAttributeAudio); ok && t.Title != "" {
				if t.Performer != "" { return t.Performer+" - "+t.Title }; return t.Title
			}
			if f, ok := attr.(*telegram.DocumentAttributeFilename); ok && f.FileName != "" { return f.FileName }
		}
	}
	return "telegram-media"
}
func sanitize(name string) string {
	return strings.NewReplacer("/", "_", "\\", "_", ":", "_", "*", "_", "?", "_", "\" ", "_", "<", "_", ">", "_", "|", "_", " ", "_").Replace(name)
}
