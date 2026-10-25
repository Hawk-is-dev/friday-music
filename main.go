package main

import (
	"log"
	"log/slog"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"

	"github.com/amarnathcjd/gortc"
	"github.com/amarnathcjd/gogram/telegram"
)

func main() {
	loadEnv(".env")
	for _, key := range []string{"BOT_TOKEN", "API_ID", "API_HASH", "SESSION_STRING"} {
		if strings.TrimSpace(os.Getenv(key)) == "" {
			log.Fatalf("missing required environment variable: %s", key)
		}
	}

	// Railway variables can accidentally include surrounding quotes or newlines.
	// Normalize harmless surrounding whitespace, but never print the secret itself.
	sessionString := strings.TrimSpace(os.Getenv("SESSION_STRING"))
	if strings.ContainsAny(sessionString, "\r\n\t ") {
		log.Fatal("SESSION_STRING contains embedded whitespace; paste the raw, single-line Gogram session string without quotes")
	}
	if !strings.HasPrefix(sessionString, "1BvE") && !strings.HasPrefix(sessionString, "1BvX") {
		log.Fatalf("SESSION_STRING does not look like a Gogram string session (expected prefix 1BvE or legacy 1BvX); regenerate/export it with the same Gogram library version used by FRIDAY")
	}

	apiID, err := strconv.Atoi(mustEnv("API_ID"))
	if err != nil || apiID <= 0 {
		log.Fatalf("invalid API_ID: must be a positive integer")
	}
	apiHash := mustEnv("API_HASH")

	botClient, err := telegram.NewClient(telegram.ClientConfig{
		AppID: int32(apiID), AppHash: apiHash, Session: "friday-bot.session",
	})
	if err != nil {
		log.Fatalf("create bot client: %v", err)
	}
	if err := botClient.LoginBot(mustEnv("BOT_TOKEN")); err != nil {
		log.Fatalf("login bot: %v", err)
	}

	assistant, err := telegram.NewClient(telegram.ClientConfig{
		AppID: int32(apiID), AppHash: apiHash,
		StringSession: sessionString, Session: "friday-assistant.session",
	})
	if err != nil {
		log.Fatalf("create assistant client: %v; SESSION_STRING passed basic format checks, so export it again with Gogram's ExportStringSession() using the same Gogram version pinned in go.mod. Do not paste the session into logs or chat", err)
	}
	if _, err := assistant.Conn(); err != nil {
		log.Fatalf("connect assistant account: %v", err)
	}
	if _, err := assistant.GetMe(); err != nil {
		log.Fatalf("assistant user session required: %v", err)
	}

	level := slog.LevelInfo
	switch strings.ToLower(strings.TrimSpace(os.Getenv("LOG_LEVEL"))) {
	case "debug":
		level = slog.LevelDebug
	case "warn", "warning":
		level = slog.LevelWarn
	case "error":
		level = slog.LevelError
	}

	downDir := os.Getenv("DOWNLOAD_DIR")
	if downDir == "" {
		downDir = "downloads"
	}
	if err := os.MkdirAll(downDir, 0o755); err != nil {
		log.Fatalf("create download directory: %v", err)
	}

	b := &bot{
		client: botClient, assistant: assistant, mgr: newManager(),
		logLevel: gortc.WithLogger(gortc.NewLogger(level)), downDir: downDir,
	}
	b.register()

	if me, err := botClient.GetMe(); err == nil {
		log.Printf("FRIDAY Music is online as @%s", me.Username)
	}
	log.Println("Commands: /start /help /play /vplay /vp9play /skip /pause /resume /stop /end /leave /volume /queue /shuffle /playing /stats /participants")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Println("FRIDAY Music shutting down")
	b.mgr.shutdownAll()
	_ = assistant.Terminate()
	_ = botClient.Terminate()
}
