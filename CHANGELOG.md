# Changelog

All notable changes to this project will be documented in this file.

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
