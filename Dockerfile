FROM golang:1.25.3-bookworm AS build
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
# The repository currently has no go.sum. Generate and verify dependency checksums
# after source files are present, before compiling.
RUN go mod tidy && go mod verify && CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o /out/friday .

FROM denoland/deno:bin-2.9.8 AS deno

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates ffmpeg python3 python3-pip \
    && python3 -m pip install --break-system-packages --no-cache-dir -U "yt-dlp[default]" \
    && rm -rf /var/lib/apt/lists/*
COPY --from=deno /deno /usr/local/bin/deno
WORKDIR /app
COPY --from=build /out/friday /app/friday
RUN mkdir -p /app/downloads
ENV DOWNLOAD_DIR=/app/downloads
CMD ["/app/friday"]
