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
	for _, key := range []string{"BOT_TOKEN", "API_ID", "API_HASH"} {
		if strings.TrimSpace(os.Getenv(key)) == "" {
			log.Fatalf("missing required environment variable: %s", key)
		}
	}

	// SESSION_STRING is optional during first startup so the owner can generate it
	// through /gensession. Never print the value itself.
	sessionString := strings.TrimSpace(os.Getenv("SESSION_STRING"))
	if strings.ContainsAny(sessionString, "\r\n\t ") {
		log.Printf("SESSION_STRING contains embedded whitespace; assistant login will be skipped. Regenerate it with /gensession.")
		sessionString = ""
	}
	if sessionString != "" && !strings.HasPrefix(sessionString, "1BvE") && !strings.HasPrefix(sessionString, "1BvX") {
		log.Printf("SESSION_STRING format is not recognized by this Gogram version; assistant login will be skipped. Use /gensession to regenerate it.")
		sessionString = ""
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

	var assistant *telegram.Client
	if sessionString != "" {
		assistantClient, assistantErr := telegram.NewClient(telegram.ClientConfig{
			AppID: int32(apiID), AppHash: apiHash,
			StringSession: sessionString, Session: "friday-assistant.session",
		})
		if assistantErr != nil {
			log.Printf("assistant session could not be loaded: %v; bot will stay online so /gensession can be used", assistantErr)
		} else if _, assistantErr = assistantClient.Conn(); assistantErr != nil {
			log.Printf("assistant account connection failed: %v; bot will stay online so /gensession can be used", assistantErr)
			_ = assistantClient.Terminate()
		} else if _, assistantErr = assistantClient.GetMe(); assistantErr != nil {
			log.Printf("assistant user session is not authorized: %v; bot will stay online so /gensession can be used", assistantErr)
			_ = assistantClient.Terminate()
		} else {
			assistant = assistantClient
		}
	} else {
		log.Println("No valid SESSION_STRING configured; FRIDAY is online in setup mode. Use /gensession in the owner's private chat.")
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
	log.Println("Commands: /start /help /gensession /sessionphone /sessioncode /sessionpassword /play /vplay /vp9play /skip /pause /resume /stop /end /leave /volume /queue /shuffle /playing /stats /participants")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Println("FRIDAY Music shutting down")
	b.mgr.shutdownAll()
	if assistant != nil { _ = assistant.Terminate() }
	_ = botClient.Terminate()
}
