FROM golang:1.25.3-bookworm AS build
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o /out/friday .

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates ffmpeg yt-dlp && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /out/friday /app/friday
RUN mkdir -p /app/downloads
ENV DOWNLOAD_DIR=/app/downloads
CMD ["/app/friday"]
