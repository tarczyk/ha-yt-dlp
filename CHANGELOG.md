# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.22] - 2026-11-20

### Fixed
- Chrome extension popup: replaced leftover legacy color tokens with the new theme tokens so cancelled/status and system health styles render correctly in light and dark modes.

## [1.0.21] - 2026-11-20

### Changed
- Redesigned the Chrome extension popup with a dark header, settings icon, lighter cards, and improved light/dark theme presentation.
- Added a `Paste` button for the video URL field and a collapsible `More formats` section for advanced format choices.
- Kept existing download, task status/progress, cancel action, Media Browser link, and HA settings behavior intact.

## [1.0.20] - 2026-11-19

### Added
- Best Video profile (`format: "best_video"`): best video + audio without re-encoding, merged into WebM (AV1/VP9 + Opus), MP4 only for H.264-only sources, never MKV. Files are named `Title [best].<ext>`. Available in the HA card and the Chrome extension, with a compatibility hint.
- Best Audio profile (`format: "best_audio"`): the source's best audio stream without re-encoding, `Title [best].opus` on YouTube. AAC-only sources produce `Title [best].m4a`, which HA hides from the WiiM; use MP3 there. Sources without an audio-only stream fall back to the audio of a progressive file, still copied; audio that cannot be copied fails instead of being converted. `.opus` files are listed, served (`audio/ogg`) and deletable. Available in the HA card and the Chrome extension.
- Add-on option `max_video_height` (optional, empty by default): caps the resolution of the MP4 and Best Video profiles, e.g. `2160` so a 4K TV never gets 8K files. MP3 and Best Audio ignore it.

### Changed
- MP4 profile now selects H.264 + AAC so files play on DLNA TVs (AV1/VP9 in MP4 was rejected, e.g. Samsung Q80A, UPnP error 701). MP4 downloads drop from up to 4K to H.264, typically 1080p on YouTube; 4K is available via the Best Video profile.
- Every MP4 file is written with the index at the start (`+faststart`), including progressive (non-merged) downloads.
- MP4 falls back to the best MP4-compatible streams (possibly AV1/VP9) only when the source has no H.264 + AAC at all; the download still succeeds.
- Sources without H.264 still download via the previous MP4-compatible fallback.

## [1.0.19] - 2026-09-04

### Fixed
- Enable `homeassistant_api` so HA notifications and `ha_yt_dlp_update_failed` events work (fixes HTTP 401).
- Add optional `cookies_file` option (default `youtube_cookies.txt`) with `/config` read-only map for YouTube auth.
- Run `pip install -U yt-dlp` with `--break-system-packages` in the updater (fixes exit code 1 on Alpine).
- Log pip stderr when yt-dlp auto-update fails.

## [1.0.17] - 2026-05-03

### Changed
- Bumped Chrome extension version to `1.0.17`.
- Updated `package.json` and `yt-dlp-api/config.yaml` to version `1.0.17`.

### Fixed
- Updated `aquasecurity/trivy-action` in the security-scan workflow to `v0.36.0` (the previously referenced `0.30.0` did not exist and caused CI failures).

## [1.0.16] - prior release

- Initial public release of the HA yt-dlp Chrome extension (Manifest V3).
- 1-click YouTube → HA yt-dlp Docker API download from the browser toolbar.
- Configurable API URL stored in `chrome.storage.sync`.
- Background service worker for fallback tab opening.
