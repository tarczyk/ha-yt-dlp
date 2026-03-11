#!/usr/bin/env bash
# bump-version.sh — update version in all files and create git tag
# Usage: ./bump-version.sh 1.0.14

set -euo pipefail

NEW_VERSION="${1:-}"

if [[ -z "$NEW_VERSION" ]]; then
  echo "Usage: ./bump-version.sh <new-version>"
  echo "Example: ./bump-version.sh 1.0.14"
  exit 1
fi

# Validate semver format
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: version must be in X.Y.Z format (e.g. 1.0.14)"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FILES=(
  "$SCRIPT_DIR/yt-dlp-api/config.yaml"
  "$SCRIPT_DIR/chrome-ext/manifest.json"
  "$SCRIPT_DIR/package.json"
)

# Check all files exist
for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Error: file not found: $f"
    exit 1
  fi
done

# Detect current version from config.yaml
CURRENT_VERSION=$(grep '^version:' "$SCRIPT_DIR/yt-dlp-api/config.yaml" | sed 's/version: "\(.*\)"/\1/')

echo "Bumping version: $CURRENT_VERSION → $NEW_VERSION"
echo ""

# Update yt-dlp-api/config.yaml  (YAML: version: "X.Y.Z")
sed -i '' "s/^version: \"$CURRENT_VERSION\"/version: \"$NEW_VERSION\"/" \
  "$SCRIPT_DIR/yt-dlp-api/config.yaml"
echo "✓ yt-dlp-api/config.yaml"

# Update chrome-ext/manifest.json  (JSON: "version": "X.Y.Z")
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" \
  "$SCRIPT_DIR/chrome-ext/manifest.json"
echo "✓ chrome-ext/manifest.json"

# Update package.json  (JSON: "version": "X.Y.Z")
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" \
  "$SCRIPT_DIR/package.json"
echo "✓ package.json"

echo ""
echo "Staging files..."
git -C "$SCRIPT_DIR" add \
  yt-dlp-api/config.yaml \
  chrome-ext/manifest.json \
  package.json

git -C "$SCRIPT_DIR" commit -m "chore: bump version to $NEW_VERSION"
echo "✓ git commit"

git -C "$SCRIPT_DIR" tag "v$NEW_VERSION"
echo "✓ git tag v$NEW_VERSION"

echo ""
echo "Done. To push: git push && git push --tags"
