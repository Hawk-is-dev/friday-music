package main

import (
	"log"
	"log/slog"
	"os"
	"os/signal"
	"strconv"
	"syscall"

	"github.com/amarnathcjd/gortc"
	"github.com/amarnathcjd/gogram/telegram"
)

func main() {
	loadEnv(".env")
	apiID, err := strconv.Atoi(mustEnv("API_ID"))
	if err != nil {
		log.Fatalf("invalid API_ID: %v", err)
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
		StringSession: os.Getenv("SESSION_STRING"), Session: "friday-assistant.session",
	})
	if err != nil {
		log.Fatalf("create assistant client: %v", err)
	}
	if _, err := assistant.Conn(); err != nil {
		log.Fatalf("connect assistant account: %v", err)
	}
	if _, err := assistant.GetMe(); err != nil {
		log.Fatalf("assistant user session required: %v", err)
	}

	downDir := os.Getenv("DOWNLOAD_DIR")
	if downDir == "" { downDir = "downloads" }
	if err := os.MkdirAll(downDir, 0o755); err != nil {
		log.Fatalf("create download directory: %v", err)
	}

	b := &bot{
		client: botClient, assistant: assistant, mgr: newManager(),
		logLevel: gortc.WithLogger(gortc.NewLogger(slog.LevelInfo)), downDir: downDir,
	}
	b.register()

	if me, err := botClient.GetMe(); err == nil {
		log.Printf("FRIDAY Music is online as @%s", me.Username)
	}
	log.Println("Commands: /start /help /play /vplay /skip /pause /resume /stop /leave /volume /queue /playing /stats /participants")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Println("FRIDAY Music shutting down")
	_ = assistant.Terminate()
	_ = botClient.Terminate()
}
