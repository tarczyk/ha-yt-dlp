#!/usr/bin/env bash
# Copy the card source to repo root as ha-yt-dlp.js so HACS can find it
# (HACS Plugin requires a .js file named like the repository).
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE="$SCRIPT_DIR/yt-dlp-card.js"
DEST="$REPO_ROOT/ha-yt-dlp.js"

if [[ ! -f "$SOURCE" ]]; then
  echo "Source not found: $SOURCE"
  exit 1
fi

# Replace first comment block with HACS bundle header, keep rest of file
{
  echo "/**"
  echo " * yt-dlp-card – Home Assistant Lovelace custom card"
  echo " * Bundled as ha-yt-dlp.js for HACS (repository name must match filename)."
  echo " * Source: frontend/ha-card/yt-dlp-card.js"
  echo " *"
  echo " * Config: api_url, title, max_tasks. Type in Lovelace: custom:yt-dlp-card"
  echo " */"
  tail -n +10 "$SOURCE"
} > "$DEST"
echo "Updated $DEST from $SOURCE"
