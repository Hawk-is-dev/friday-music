package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/amarnathcjd/gogram/telegram"
)

type sessionFlow struct {
	ctx      context.Context
	cancel   context.CancelFunc
	code     chan string
	password chan string
	started  bool
}

const configuredOwnerID int64 = 6572631282

func (b *bot) sessionOwnerMessage(m *telegram.NewMessage) bool {
	return m.IsPrivate() && m.SenderID() == configuredOwnerID
}

func (b *bot) startSessionGeneration(m *telegram.NewMessage) error {
	if !b.sessionOwnerMessage(m) {
		return reply2(m, "⛔ This command is available only to the configured owner in private chat.")
	}

	b.sessionMu.Lock()
	if b.sessionFlow != nil {
		b.sessionMu.Unlock()
		return reply2(m, "A session-generation flow is already active. Finish it or wait for it to expire.")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	flow := &sessionFlow{ctx: ctx, cancel: cancel, code: make(chan string, 1), password: make(chan string, 1)}
	b.sessionFlow = flow
	b.sessionMu.Unlock()

	_, _ = b.client.SendMessage(m.ChatID(), "✦ FRIDAY SESSION SETUP\nSend your phone number with country code using:\n/sessionphone +91XXXXXXXXXX\n\nUse only your own Telegram account. The flow expires in 10 minutes.")
	go func() {
		<-ctx.Done()
		b.clearSessionFlow(flow)
	}()
	return nil
}

func (b *bot) handleSessionPhone(m *telegram.NewMessage) error {
	if !b.sessionOwnerMessage(m) {
		return reply2(m, "⛔ Owner-only command. Use this in private chat.")
	}
	phone := strings.TrimSpace(m.Args())
	_, _ = m.Delete()
	if phone == "" {
		return b.sendSessionPrompt(m.ChatID(), "Usage: /sessionphone +91XXXXXXXXXX")
	}

	b.sessionMu.Lock()
	flow := b.sessionFlow
	if flow == nil || flow.ctx.Err() != nil {
		b.sessionMu.Unlock()
		return b.sendSessionPrompt(m.ChatID(), "No active setup. Start with /gensession.")
	}
	if flow.started {
		b.sessionMu.Unlock()
		return b.sendSessionPrompt(m.ChatID(), "Login has already started. Follow the OTP/password prompts.")
	}
	flow.started = true
	b.sessionMu.Unlock()

	go b.runSessionLogin(m.ChatID(), phone, flow)
	return nil
}

func (b *bot) handleSessionCode(m *telegram.NewMessage) error {
	return b.submitSessionInput(m, true)
}

func (b *bot) handleSessionPassword(m *telegram.NewMessage) error {
	return b.submitSessionInput(m, false)
}

func (b *bot) submitSessionInput(m *telegram.NewMessage, isCode bool) error {
	if !b.sessionOwnerMessage(m) {
		return reply2(m, "⛔ Owner-only command. Use this in private chat.")
	}
	value := strings.TrimSpace(m.Args())
	_, _ = m.Delete()
	if value == "" {
		if isCode {
			return b.sendSessionPrompt(m.ChatID(), "Usage: /sessioncode <Telegram login code>")
		}
		return b.sendSessionPrompt(m.ChatID(), "Usage: /sessionpassword <2-step verification password>")
	}

	b.sessionMu.Lock()
	flow := b.sessionFlow
	b.sessionMu.Unlock()
	if flow == nil || flow.ctx.Err() != nil || !flow.started {
		return b.sendSessionPrompt(m.ChatID(), "No active login is waiting for input. Start with /gensession.")
	}

	ch := flow.password
	if isCode {
		ch = flow.code
	}
	select {
	case ch <- value:
		return b.sendSessionPrompt(m.ChatID(), "Received. Continue with the next prompt.")
	default:
		return b.sendSessionPrompt(m.ChatID(), "An input is already waiting; follow the latest prompt.")
	}
}

func (b *bot) runSessionLogin(chatID int64, phone string, flow *sessionFlow) {
	defer b.clearSessionFlow(flow)

	apiID, err := strconv.Atoi(strings.TrimSpace(os.Getenv("API_ID")))
	if err != nil || apiID <= 0 {
		b.sendSessionPrompt(chatID, "SESSION SETUP FAILED: API_ID is missing or invalid.")
		return
	}
	apiHash := strings.TrimSpace(os.Getenv("API_HASH"))
	if apiHash == "" {
		b.sendSessionPrompt(chatID, "SESSION SETUP FAILED: API_HASH is missing.")
		return
	}

	userClient, err := telegram.NewClient(telegram.ClientConfig{
		AppID: int32(apiID),
		AppHash: apiHash,
		Session: "friday-generated.session",
		SessionName: "friday-session-generator",
	})
	if err != nil {
		b.sendSessionPrompt(chatID, "SESSION SETUP FAILED while creating the login client: "+brief(err.Error(), 300))
		return
	}
	defer func() { _ = userClient.Terminate() }()

	waitFor := func(kind string, ch <-chan string) (string, error) {
		prompt := "Send the Telegram login code using /sessioncode <code>."
		if kind == "password" {
			prompt = "Two-step verification is enabled. Send it using /sessionpassword <password>."
		}
		if _, err := b.client.SendMessage(chatID, prompt); err != nil {
			return "", err
		}
		select {
		case value := <-ch:
			return value, nil
		case <-flow.ctx.Done():
			return "", errors.New("session setup timed out or was cancelled")
		}
	}

	_, err = userClient.Login(phone, &telegram.LoginOptions{
		Ctx: flow.ctx,
		MaxRetries: 3,
		CodeCallback: func() (string, error) { return waitFor("code", flow.code) },
		PasswordCallback: func() (string, error) { return waitFor("password", flow.password) },
	})
	if err != nil {
		b.sendSessionPrompt(chatID, "SESSION LOGIN FAILED: "+brief(err.Error(), 400)+"\nStart again with /gensession. Never share your login code or 2-step password.")
		return
	}

	sessionString := userClient.ExportStringSession()
	if sessionString == "" || (!strings.HasPrefix(sessionString, "1BvE") && !strings.HasPrefix(sessionString, "1BvX")) {
		b.sendSessionPrompt(chatID, "Login succeeded, but Gogram did not return a recognized string-session format. Please retry with the pinned FRIDAY Gogram version.")
		return
	}

	text := fmt.Sprintf("✦ FRIDAY SESSION GENERATED\n\nCopy the full value below into Railway → Variables → STRING_SESSION, then restart FRIDAY. FRIDAY cannot edit hosting variables automatically.\n\n%s\n\nThis is a private account credential. Do not forward it or post it in GitHub. After saving it in Railway, delete this message.", sessionString)
	_, _ = b.client.SendMessage(chatID, text)
}

func (b *bot) sendSessionPrompt(chatID int64, text string) error {
	_, err := b.client.SendMessage(chatID, text)
	return err
}

func (b *bot) clearSessionFlow(flow *sessionFlow) {
	b.sessionMu.Lock()
	defer b.sessionMu.Unlock()
	if b.sessionFlow == flow {
		b.sessionFlow = nil
		flow.cancel()
	}
}

