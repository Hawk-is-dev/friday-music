package main

import (
	"reflect"
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
