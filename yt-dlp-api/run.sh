#!/usr/bin/with-contenv bashio

PORT=$(bashio::config 'port')
export PORT="${PORT:-5000}"

# Subdir under /media (e.g. youtube_downloads → /media/youtube_downloads). Only safe chars.
MEDIA_SUBDIR=$(bashio::config 'media_subdir' 'youtube_downloads')
MEDIA_SUBDIR=$(echo "$MEDIA_SUBDIR" | sed -n 's/^[a-zA-Z0-9_.-]*$/\0/p')
[[ -z "$MEDIA_SUBDIR" ]] && MEDIA_SUBDIR="youtube_downloads"
export MEDIA_SUBDIR
export DOWNLOAD_DIR="/media/${MEDIA_SUBDIR}"
mkdir -p "$DOWNLOAD_DIR"

# Optional Netscape cookies file under /config (e.g. youtube_cookies.txt).
COOKIES_FILE=$(bashio::config 'cookies_file' '')
if [[ -n "$COOKIES_FILE" ]]; then
    COOKIES_BASENAME=$(basename "$COOKIES_FILE")
    if [[ "$COOKIES_BASENAME" == "$COOKIES_FILE" ]]; then
        export COOKIES_FILE="/config/${COOKIES_BASENAME}"
    else
        bashio::log.warning "cookies_file must be a filename under /config — ignoring: ${COOKIES_FILE}"
        unset COOKIES_FILE
    fi
else
    unset COOKIES_FILE
fi

exec python3 -m flask --app app run --host=0.0.0.0 --port="${PORT}"
