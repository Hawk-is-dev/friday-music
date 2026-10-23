package main

import (
	"bufio"
	"context"
	"fmt"
	"math/rand"
	"os"
	"strings"
	"sync"

	"github.com/amarnathcjd/gortc"
)

type track struct {
	title string
	path string
	video bool
	vp9 bool
}

type session struct {
	mu sync.Mutex
	mgr *manager
	chatID int64
	call *gortc.Call
	queue []track
	current *track
	player *gortc.Player
	gen uint64
	playing bool
	volume int
	useVP9 bool
	lastBwe gortc.BandwidthEstimate
	joinedAt map[int64]bool
}

type manager struct {
	mu sync.Mutex
	sessions map[int64]*session
}

type clientFactory func(vp9 bool) *gortc.Call

func newManager() *manager { return &manager{sessions: map[int64]*session{}} }

func (m *manager) get(chatID int64) *session {
	m.mu.Lock()
	defer m.mu.Unlock()
	s := m.sessions[chatID]
	if s == nil {
		s = &session{mgr:m, chatID:chatID, volume:100, joinedAt:map[int64]bool{}}
		m.sessions[chatID] = s
	}
	return s
}

func (m *manager) drop(chatID int64) {
	m.mu.Lock()
	delete(m.sessions, chatID)
	m.mu.Unlock()
}

func (s *session) enqueue(t track) (int, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.queue = append(s.queue, t)
	if !s.playing { return 0, true }
	return len(s.queue), false
}

func (s *session) ensureCall(factory clientFactory, chatID any) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.call != nil { return nil }
	call := factory(s.useVP9)
	call.OnParticipant(func(ev gortc.ParticipantEvent, p gortc.Participant) {
		s.mu.Lock()
		switch ev {
		case gortc.ParticipantJoined: s.joinedAt[p.PeerID] = true
		case gortc.ParticipantLeft: delete(s.joinedAt, p.PeerID)
		}
		s.mu.Unlock()
	})
	call.OnBandwidthEstimate(func(e gortc.BandwidthEstimate) {
		s.mu.Lock(); s.lastBwe = e; s.mu.Unlock()
	})
	if err := call.Join(chatID); err != nil { return err }
	s.call = call
	return nil
}

func (s *session) startNext() {
	s.mu.Lock()
	if p := s.player; p != nil {
		s.gen++ // invalidate the old player's completion callback before stopping it
		s.player = nil
		s.mu.Unlock()
		p.Stop()
		<-p.Done()
		s.mu.Lock()
	}
	if len(s.queue) == 0 {
		s.playing = false
		s.current = nil
		call := s.call
		s.call = nil
		s.mu.Unlock()
		if call != nil { _ = call.Leave() }
		s.mgr.drop(s.chatID)
		return
	}
	next := s.queue[0]
	s.queue = s.queue[1:]
	s.current = &next
	s.playing = true
	s.gen++
	gen := s.gen
	call := s.call
	ctx, cancel := context.WithCancel(context.Background())
	player := call.Play(ctx, sourceFor(next))
	s.player = player
	s.mu.Unlock()

	if call != nil { _ = call.SetVideoStopped(!next.video) }
	go func() {
		<-player.Done()
		cancel()
		removeFile(next.path)
		s.mu.Lock()
		stale := gen != s.gen
		s.mu.Unlock()
		if !stale { s.startNext() }
	}()
}

func (s *session) skip() bool {
	s.mu.Lock()
	ok := s.player != nil || len(s.queue) > 0
	s.mu.Unlock()
	if ok { s.startNext() }
	return ok
}

func (s *session) pause() bool {
	s.mu.Lock(); defer s.mu.Unlock()
	if s.player == nil || s.player.Paused() { return false }
	s.player.Pause(); return true
}
func (s *session) resume() bool {
	s.mu.Lock(); defer s.mu.Unlock()
	if s.player == nil || !s.player.Paused() { return false }
	s.player.Resume(); return true
}
func (s *session) stop() {
	s.mu.Lock()
	for _, t := range s.queue { removeFile(t.path) }
	s.queue = nil
	p := s.player; s.player = nil; s.current = nil; s.playing = false; s.gen++
	s.mu.Unlock()
	if p != nil { p.Stop() }
}
func (s *session) leave() error {
	s.stop()
	s.mu.Lock(); call := s.call; s.call = nil; s.mu.Unlock()
	if call != nil { return call.Leave() }
	return nil
}
func (s *session) setVolume(percent int) error {
	s.mu.Lock(); call := s.call; s.volume = percent; s.mu.Unlock()
	if call == nil { return fmt.Errorf("not in a voice chat") }
	return call.SetVolume(percent)
}
func (s *session) nowPlaying() (string, bool) {
	s.mu.Lock(); defer s.mu.Unlock()
	if s.current == nil { return "", false }
	return s.current.title, true
}
func (s *session) list() []track {
	s.mu.Lock(); defer s.mu.Unlock()
	return append([]track(nil), s.queue...)
}
func sourceFor(t track) gortc.Source {
	if t.video { opt := gortc.Res720; if t.vp9 { opt = opt.With(gortc.EncodeOptions{VideoCodec:gortc.VideoCodecVP9}) }; return gortc.FromFile(t.path, opt) }
	return gortc.FromFile(t.path, gortc.EncodeOptions{Tracks:gortc.TrackAudio})
}
func removeFile(path string) { if path != "" { _ = os.Remove(path) } }

func loadEnv(path string) {
	f, err := os.Open(path); if err != nil { return }; defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") { continue }
		key, val, ok := strings.Cut(line, "="); if !ok { continue }
		key = strings.TrimSpace(key); val = strings.Trim(strings.TrimSpace(val), `"'`)
		if _, exists := os.LookupEnv(key); !exists { _ = os.Setenv(key, val) }
	}
}
func mustEnv(key string) string { v := os.Getenv(key); if v == "" { logFatalMissingEnv(key) }; return v }
func logFatalMissingEnv(key string) { panic("missing required environment variable: " + key) }

func (s *session) shuffle() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.queue) < 2 { return len(s.queue) }
	rand.Shuffle(len(s.queue), func(i, j int) {
		s.queue[i], s.queue[j] = s.queue[j], s.queue[i]
	})
	return len(s.queue)
}
