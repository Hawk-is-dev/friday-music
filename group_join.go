package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

// tryAutoJoinAssistant asks Telegram to create a short-lived, single-use invite
// link for this chat, then asks the assistant user session to join through it.
// The bot must be an administrator with permission to invite users. The caller
// should still attempt voice-chat Join afterwards: import may report that the
// assistant is already a member, which is fine.
func (b *bot) tryAutoJoinAssistant(chatID int64) error {
	token := strings.TrimSpace(getBotToken())
	if token == "" {
		return fmt.Errorf("BOT_TOKEN is not configured")
	}

	form := url.Values{}
	form.Set("chat_id", fmt.Sprintf("%d", chatID))
	form.Set("name", "FRIDAY assistant auto-join")
	form.Set("expire_date", fmt.Sprintf("%d", time.Now().Add(10*time.Minute).Unix()))
	form.Set("member_limit", "1")

	req, err := http.NewRequest(http.MethodPost,
		"https://api.telegram.org/bot"+token+"/createChatInviteLink",
		strings.NewReader(form.Encode()))
	if err != nil {
		return fmt.Errorf("create invite request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	client := &http.Client{Timeout: 12 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("create assistant invite link: %w", err)
	}
	defer resp.Body.Close()

	var result struct {
		OK          bool   `json:"ok"`
		Description string `json:"description"`
		Result      struct {
			InviteLink string `json:"invite_link"`
		} `json:"result"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("read invite response: %w", err)
	}
	if !result.OK || result.Result.InviteLink == "" {
		if result.Description == "" {
			result.Description = fmt.Sprintf("Telegram returned HTTP %d", resp.StatusCode)
		}
		return fmt.Errorf("Telegram could not create an invite link: %s (make the bot an admin with invite-user permission)", result.Description)
	}

	hash, err := inviteHash(result.Result.InviteLink)
	if err != nil {
		return err
	}
	_, err = b.assistant.MessagesImportChatInvite(hash)
	if err != nil {
		// The assistant may already be a member. The subsequent voice-chat Join
		// in enqueueTrack will verify whether it can actually access the group.
		return fmt.Errorf("assistant invite import: %w", err)
	}
	return nil
}

func inviteHash(link string) (string, error) {
	u, err := url.Parse(strings.TrimSpace(link))
	if err != nil {
		return "", fmt.Errorf("invalid Telegram invite link: %w", err)
	}
	path := strings.Trim(u.Path, "/")
	if strings.HasPrefix(path, "+") {
		path = strings.TrimPrefix(path, "+")
	} else if strings.HasPrefix(path, "joinchat/") {
		path = strings.TrimPrefix(path, "joinchat/")
	} else {
		return "", fmt.Errorf("unsupported Telegram invite-link format")
	}
	if path == "" {
		return "", fmt.Errorf("Telegram invite link has no invite hash")
	}
	return path, nil
}

// getBotToken is separated so the token is never copied into logs or messages.
func getBotToken() string {
	return strings.TrimSpace(os.Getenv("BOT_TOKEN"))
}
