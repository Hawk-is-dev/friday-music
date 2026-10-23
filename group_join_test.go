package main

import "testing"

func TestInviteHash(t *testing.T) {
	tests := []struct {
		link string
		want string
	}{
		{"https://t.me/+AbCdEf123", "AbCdEf123"},
		{"https://t.me/joinchat/AbCdEf123", "AbCdEf123"},
	}
	for _, tt := range tests {
		got, err := inviteHash(tt.link)
		if err != nil {
			t.Fatalf("inviteHash(%q): %v", tt.link, err)
		}
		if got != tt.want {
			t.Errorf("inviteHash(%q) = %q, want %q", tt.link, got, tt.want)
		}
	}
}

func TestInviteHashRejectsPublicUsername(t *testing.T) {
	if _, err := inviteHash("https://t.me/publicgroup"); err == nil {
		t.Fatal("expected a public username URL to be rejected as an invite link")
	}
}
