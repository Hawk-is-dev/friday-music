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
	closed bool
	loop bool
	loopQueue bool
	volume int
	useVP9 bool
	lastBwe gortc.BandwidthEstimate
	joinedAt map[int64]bool
}

const maxQueuedTracks = 50

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

func (m *manager) dropIfSame(chatID int64, expected *session) {
	m.mu.Lock()
	if m.sessions[chatID] == expected {
		delete(m.sessions, chatID)
	}
	m.mu.Unlock()
}

func (s *session) enqueueTrack(factory clientFactory, chatID any, t track) (int, bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed {
		return 0, false, fmt.Errorf("playback session is closed; retry the command")
	}
	if len(s.queue) >= maxQueuedTracks {
		return 0, false, fmt.Errorf("queue limit reached (%d upcoming tracks)", maxQueuedTracks)
	}
	if s.call == nil {
		call := factory(s.useVP9)
		call.OnParticipant(func(ev gortc.ParticipantEvent, p gortc.Participant) {
			s.mu.Lock()
			switch ev {
			case gortc.ParticipantJoined:
				s.joinedAt[p.PeerID] = true
			case gortc.ParticipantLeft:
				delete(s.joinedAt, p.PeerID)
			}
			s.mu.Unlock()
		})
		call.OnBandwidthEstimate(func(e gortc.BandwidthEstimate) {
			s.mu.Lock()
			s.lastBwe = e
			s.mu.Unlock()
		})
		if err := call.Join(chatID); err != nil {
			return 0, false, err
		}
		s.call = call
	}
	s.queue = append(s.queue, t)
	if !s.playing {
		s.playing = true
		return 0, true, nil
	}
	return len(s.queue), false, nil
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
		s.closed = true
		call := s.call
		s.call = nil
		s.mgr.dropIfSame(s.chatID, s)
		s.mu.Unlock()
		if call != nil { _ = call.Leave() }
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
		s.mu.Lock()
		stale := gen != s.gen
		keepForLoop := !stale && (s.loop || s.loopQueue)
		if !stale && s.loop {
			s.queue = append([]track{next}, s.queue...)
		} else if !stale && s.loopQueue {
			s.queue = append(s.queue, next)
		}
		s.mu.Unlock()
		if !keepForLoop {
			removeFile(next.path)
		}
		if !stale {
			s.startNext()
		}
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
	if p != nil {
		p.Stop()
		<-p.Done()
	}
}
func (s *session) leave() error {
	s.stop()
	s.mu.Lock()
	s.closed = true
	call := s.call
	s.call = nil
	s.mu.Unlock()
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

func (m *manager) shutdownAll() {
	m.mu.Lock()
	sessions := make([]*session, 0, len(m.sessions))
	for _, s := range m.sessions {
		sessions = append(sessions, s)
	}
	m.mu.Unlock()
	for _, s := range sessions {
		_ = s.leave()
		m.dropIfSame(s.chatID, s)
	}
}

func (s *session) toggleLoop() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.loop = !s.loop
	if s.loop { s.loopQueue = false }
	return s.loop
}

func (s *session) loopEnabled() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.loop
}

func (s *session) toggleLoopQueue() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.loopQueue = !s.loopQueue
	if s.loopQueue { s.loop = false }
	return s.loopQueue
}

func (s *session) loopQueueEnabled() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.loopQueue
}

func (s *session) clearQueue() int {
	s.mu.Lock()
	queued := s.queue
	s.queue = nil
	s.mu.Unlock()
	for _, t := range queued {
		removeFile(t.path)
	}
	return len(queued)
}

func (s *session) removeQueued(index int) (track, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if index < 1 || index > len(s.queue) {
		return track{}, false
	}
	idx := index - 1
	removed := s.queue[idx]
	s.queue = append(s.queue[:idx], s.queue[idx+1:]...)
	return removed, true
}

func (s *session) shuffle() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.queue) < 2 { return len(s.queue) }
	rand.Shuffle(len(s.queue), func(i, j int) {
		s.queue[i], s.queue[j] = s.queue[j], s.queue[i]
	})
	return len(s.queue)
}
