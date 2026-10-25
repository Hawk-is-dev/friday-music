package main

import (
	"encoding/base64"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestSanitizeRemovesPathSeparatorsAndUnsafeCharacters(t *testing.T) {
	got := sanitize("../my song:demo?.mp3")
	want := ".._my_song_demo_.mp3"
	if got != want {
		t.Fatalf("sanitize() = %q, want %q", got, want)
	}
}

func TestShufflePreservesEveryQueuedTrack(t *testing.T) {
	s := &session{queue: []track{
		{title: "one", path: "1.mp3"},
		{title: "two", path: "2.mp3"},
		{title: "three", path: "3.mp3"},
	}}
	if got := s.shuffle(); got != 3 {
		t.Fatalf("shuffle() count = %d, want 3", got)
	}
	got := make([]string, 0, len(s.queue))
	for _, item := range s.queue {
		got = append(got, item.title)
	}
	want := []string{"one", "two", "three"}
	// Shuffle order is intentionally random; compare sorted membership instead.
	seen := map[string]bool{}
	for _, title := range got {
		if seen[title] {
			t.Fatalf("duplicate track after shuffle: %q", title)
		}
		seen[title] = true
	}
	for _, title := range want {
		if !seen[title] {
			t.Fatalf("track %q lost after shuffle: %v", title, got)
		}
	}
}

func TestShuffleLeavesShortQueueUnchanged(t *testing.T) {
	s := &session{queue: []track{{title: "only", path: "only.mp3"}}}
	before := append([]track(nil), s.queue...)
	if got := s.shuffle(); got != 1 {
		t.Fatalf("shuffle() count = %d, want 1", got)
	}
	if !reflect.DeepEqual(s.queue, before) {
		t.Fatalf("single-item queue changed: %#v", s.queue)
	}
}

func TestParseYtDlpMetadata(t *testing.T) {
	id, title, err := parseYtDlpMetadata("abc123\n  A Sample Track  \n")
	if err != nil {
		t.Fatal(err)
	}
	if id != "abc123" || title != "A Sample Track" {
		t.Fatalf("metadata = (%q, %q), want (%q, %q)", id, title, "abc123", "A Sample Track")
	}
	if _, _, err := parseYtDlpMetadata("\n"); err == nil {
		t.Fatal("expected an error for empty metadata")
	}
}

func TestPrepareYtDlpCookiesFromBase64(t *testing.T) {
	dir := t.TempDir()
	cookieText := "# Netscape HTTP Cookie File\nexample.com\tTRUE\t/\tFALSE\t0\tname\tvalue\n"
	t.Setenv("COOKIES_PATH", "")
	t.Setenv("COOKIES_B64", base64.StdEncoding.EncodeToString([]byte(cookieText)))
	path, cleanup, err := prepareYtDlpCookies(dir)
	if err != nil {
		t.Fatal(err)
	}
	if path == "" {
		t.Fatal("expected a temporary cookie path")
	}
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != cookieText {
		t.Fatalf("cookie content mismatch: %q", got)
	}
	cleanup()
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("temporary cookie file still exists after cleanup: %v", err)
	}
}

func TestPrepareYtDlpCookiesRejectsMissingPath(t *testing.T) {
	t.Setenv("COOKIES_PATH", filepath.Join(t.TempDir(), "missing-cookies.txt"))
	t.Setenv("COOKIES_B64", "")
	_, _, err := prepareYtDlpCookies(".")
	if err == nil || !strings.Contains(err.Error(), "COOKIES_PATH") {
		t.Fatalf("expected missing COOKIES_PATH error, got %v", err)
	}
}

func TestClosedSessionRejectsNewTrack(t *testing.T) {
	s := &session{closed: true}
	_, _, err := s.enqueueTrack(nil, int64(123), track{title: "late track"})
	if err == nil || !strings.Contains(err.Error(), "closed") {
		t.Fatalf("expected closed-session error, got %v", err)
	}
}

func TestDropIfSamePreservesReplacementSession(t *testing.T) {
	m := newManager()
	replacement := &session{mgr: m, chatID: 123}
	m.sessions[123] = replacement
	m.dropIfSame(123, &session{mgr: m, chatID: 123})
	if got := m.get(123); got != replacement {
		t.Fatal("dropIfSame removed a replacement session")
	}
}

func TestShutdownAllClosesAndDropsSessions(t *testing.T) {
	m := newManager()
	s := m.get(123)
	s.queue = []track{{title: "queued", path: filepath.Join(t.TempDir(), "queued.mp3")}}
	if err := os.WriteFile(s.queue[0].path, []byte("test"), 0o600); err != nil {
		t.Fatal(err)
	}
	m.shutdownAll()
	if _, ok := m.sessions[123]; ok {
		t.Fatal("shutdownAll left session in manager")
	}
	s.mu.Lock()
	closed := s.closed
	queueLen := len(s.queue)
	s.mu.Unlock()
	if !closed || queueLen != 0 {
		t.Fatalf("session after shutdown: closed=%v queueLen=%d", closed, queueLen)
	}
}

func TestQueueLimitRejectsExtraTrack(t *testing.T) {
	s := &session{queue: make([]track, maxQueuedTracks)}
	_, _, err := s.enqueueTrack(nil, int64(123), track{title: "overflow"})
	if err == nil || !strings.Contains(err.Error(), "queue limit") {
		t.Fatalf("expected queue limit error, got %v", err)
	}
}

func TestLoopToggle(t *testing.T) {
	s := &session{}
	if s.toggleLoop() != true || !s.loopEnabled() {
		t.Fatal("expected loop to be enabled")
	}
	if s.toggleLoop() != false || s.loopEnabled() {
		t.Fatal("expected loop to be disabled")
	}
}

func TestRemoveQueuedTrack(t *testing.T) {
	s := &session{queue: []track{
		{title: "one", path: "1.mp3"},
		{title: "two", path: "2.mp3"},
		{title: "three", path: "3.mp3"},
	}}
	removed, ok := s.removeQueued(2)
	if !ok || removed.title != "two" {
		t.Fatalf("removeQueued(2) = %#v, %v", removed, ok)
	}
	if len(s.queue) != 2 || s.queue[0].title != "one" || s.queue[1].title != "three" {
		t.Fatalf("unexpected queue after removal: %#v", s.queue)
	}
	if _, ok := s.removeQueued(0); ok {
		t.Fatal("expected invalid queue index to be rejected")
	}
}

func TestClearQueueReturnsTracksAndEmptiesQueue(t *testing.T) {
	s := &session{queue: []track{{title: "one"}, {title: "two"}}}
	if got := s.clearQueue(); got != 2 {
		t.Fatalf("clearQueue() = %d, want 2", got)
	}
	if len(s.queue) != 0 {
		t.Fatalf("queue not empty after clearQueue: %#v", s.queue)
	}
}

func TestRepeatModesAreMutuallyExclusive(t *testing.T) {
	s := &session{}
	if !s.toggleLoop() {
		t.Fatal("expected current-track repeat to enable")
	}
	if !s.toggleLoopQueue() {
		t.Fatal("expected queue repeat to enable")
	}
	if s.loopEnabled() {
		t.Fatal("queue repeat should disable current-track repeat")
	}
	if !s.loopQueueEnabled() {
		t.Fatal("queue repeat should remain enabled")
	}
}

func TestParseYtDlpDuration(t *testing.T) {
	if got, ok := parseYtDlpDuration("abc123\\nSample track\\n185.5"); !ok || got != 185.5 {
		t.Fatalf("parseYtDlpDuration() = %v, %v; want 185.5, true", got, ok)
	}
	if _, ok := parseYtDlpDuration("abc123\\nLive stream\\nNA"); ok {
		t.Fatal("expected unknown duration to be reported as unavailable")
	}
}

func TestMaxDurationMinutesDefaultsAndValidates(t *testing.T) {
	t.Setenv("MAX_DURATION_MINUTES", "")
	if got := maxDurationMinutes(); got != 30 {
		t.Fatalf("default duration = %d, want 30", got)
	}
	t.Setenv("MAX_DURATION_MINUTES", "999")
	if got := maxDurationMinutes(); got != 30 {
		t.Fatalf("invalid duration = %d, want default 30", got)
	}
	t.Setenv("MAX_DURATION_MINUTES", "45")
	if got := maxDurationMinutes(); got != 45 {
		t.Fatalf("configured duration = %d, want 45", got)
	}
}
