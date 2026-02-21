# Repository structure & principal engineer review

**Versioning:** Git tag and add-on version must match. When releasing, set `version` in `yt-dlp-api/config.yaml` (e.g. `"1.0.8"`), then tag that commit as `v1.0.8` (e.g. `git tag v1.0.8 && git push origin v1.0.8`).

## Current layout (Option A implemented)

```
ha-yt-dlp/
├── yt-dlp-api/             # Backend – single source of truth
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   └── yt_dlp_manager.py
│   ├── config.yaml          # Add-on manifest
│   ├── Dockerfile           # Add-on image (HA base)
│   ├── requirements.txt
│   ├── run.sh
│   └── DOCS.md
├── frontend/ha-card/        # Lovelace card source
├── chrome-ext/              # Chrome extension
├── Dockerfile               # Standalone image; COPY from yt-dlp-api/
├── docker-compose.yml
├── app.py                   # Dev entry (sys.path → yt-dlp-api)
├── ha-yt-dlp.js             # HACS bundle (from frontend/ha-card)
├── repository.yaml
├── hacs.json
├── tests/                   # pytest.ini: pythonpath = yt-dlp-api
└── docs/
    └── REPO-STRUCTURE.md
```

## Assessment (principal engineer)

### What works well

- **Single repo** – one version, one place for issues/PRs, one CI. Fits project size.
- **Clear product split** – add-on, Docker, card, extension are easy to find by path.
- **CI** – tests, security scan, Docker build present; multi-arch considered.
- **Docs** – README, DOCS.md, chrome README; Security section in README.

### ~~Critical issue: duplicated backend~~ (fixed – Option A)

- **Resolved:** Only **`yt-dlp-api/app/`** and **`yt-dlp-api/requirements.txt`** exist. Root `Dockerfile` copies from `yt-dlp-api/`; tests use `pytest.ini` `pythonpath = yt-dlp-api` and CI installs from `yt-dlp-api/requirements.txt`.

### Minor issues

- **Two Docker workflows** – `docker-build.yml` and `docker-publish.yml` both build from root and push; worth merging or clearly separating (e.g. one for PRs, one for release).
- **Root `package.json`** – only references `server.js`; purpose (e.g. dev server for card?) could be one line in README or removed if unused.
- **No explicit “Repository structure”** in README – new contributors don’t see at a glance where add-on vs Docker vs card live.

---

## Recommended direction: single source of truth for API

**Idea:** One place for the Flask app and deps; add-on and standalone Docker both use it.

### Option A – Canonical code in `yt-dlp-api/` (recommended)

- Treat **`yt-dlp-api/`** as the only backend: keep **`yt-dlp-api/app/`** and **`yt-dlp-api/requirements.txt`**.
- **Remove** root **`app/`** and root **`requirements.txt`**.
- **Root `Dockerfile`** (standalone) copies from `yt-dlp-api/`:
  - `COPY yt-dlp-api/requirements.txt .`
  - `COPY yt-dlp-api/app/ ./app/`
- **Tests** at root: run with `PYTHONPATH=yt-dlp-api pytest tests/` (or `python -m pytest` from root with `PYTHONPATH=yt-dlp-api`), so imports stay `from app ...`.
- **Local dev** (e.g. `flask run`): run from repo root with `PYTHONPATH=yt-dlp-api` and `FLASK_APP=app` (or a small wrapper in `app.py` that adds `yt-dlp-api` to `sys.path` and runs the app).
- Add-on build is unchanged (already uses `yt-dlp-api/`).

Result: no duplicate `app/`, one place to change API code; add-on and Docker stay in sync.

### Option B – Canonical code at root

- Keep **root `app/`** as source of truth.
- Add-on build cannot use parent context when HA builds from `yt-dlp-api/`. So you need either:
  - A **CI step** that copies `app/` and `requirements.txt` from root into `yt-dlp-api/` before building/publishing the add-on, or
  - A **post-merge script** (e.g. GitHub Action) that syncs root → `yt-dlp-api/` so the repo on `main` always has `yt-dlp-api/app/` filled for the store.

Option B avoids changing root Dockerfile and test layout but adds sync logic and possible drift if someone edits only `yt-dlp-api/app/`.

---

## Target structure (implemented)

See **Current layout** above. No `app/` or `requirements.txt` at root; all API changes happen under `yt-dlp-api/`. Root `Dockerfile` copies from `yt-dlp-api/`; `app.py` adds `yt-dlp-api` to `sys.path`; `pytest.ini` sets `pythonpath = yt-dlp-api`.

---

## Summary

| Aspect              | Verdict |
|---------------------|--------|
| Monorepo            | ✅ Keep one repo. |
| Duplicate `app/`     | ✅ Fixed – single source in `yt-dlp-api/` (Option A). |
| README              | ✅ Add “Repository structure” and clear TOC/sections. |
| CI (two Docker jobs)| ⚠️ Prefer one workflow (build + push) or document why two. |
| Overall             | Option A implemented; one source of truth for the API. |

