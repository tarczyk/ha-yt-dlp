# Changelog

All notable changes to this project will be documented in this file.

## [1.0.18] - 2026-09-04

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
