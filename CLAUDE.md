# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

"Report That Pantry" (reportthatpantry.org) — a Flask site that helps Little Free Pantry stewards keep their pantries stocked. QR codes on physical pantries link to per-pantry pages where the public can report fullness (with an optional photo, auto-analyzed by AI); subscribers get notified by email when a pantry is reported empty. Live in production since March 2020, running in Eugene, Oregon.

## Commands

There is no build tooling, test suite, linter config, or CI pipeline in this repo — the commands below are everything available.

**Setup / run locally:**
```bash
source venv/bin/activate        # canonical venv (new_venv/ and ml-venv/ are stray, unrelated to the app)
pip install -r requirements.txt
python main.py                  # runs with debug=True, reads FLASK_ENV from .env (default: DevelopmentConfig)
```

**Database migrations (Flask-Migrate/Alembic):**
```bash
flask db migrate -m "message"
flask db upgrade
```
Note: `create_database()` in `app/__init__.py` also calls `db.create_all(app=app)` on every startup, alongside migrations — a pre-existing quirk, not something to "fix" incidentally.

**Production:** deployed to Heroku (`Procfile`: `web: gunicorn main:app`), Heroku Postgres as the DB. `.claude/settings.local.json` has an allowlist of read-only `heroku pg:psql --app report-that-pantry` commands for inspecting prod data.

**No automated tests exist.** A prior commit ("Remove unnecessary test files and analysis files from root directory") removed ad hoc test scripts rather than formalizing a suite — don't assume `pytest`/`tests/` exists.

## Architecture

**App factory + two blueprints**, in `app/__init__.py`:
- `views` (`app/views.py`, ~2400 lines, mounted at `/`) — nearly everything public-facing: home/map, pantry detail + reporting, email-only location submission/verification, QR poster generation, subscribe/unsubscribe, nationwide (`/status`) and Oregon-only (`/burrito-brigade`) analytics dashboards, AI vision demo/API endpoints.
- `auth` (`app/auth.py`, mounted at `/`) — login/signup/password reset, profile, notification/subscription preferences. Contains large commented-out OAuth (flask_dance) blocks — dead code, not active.

Config is selected by `FLASK_ENV` in `config/config.py` (`ProductionConfig` / `StagingConfig` / `DevelopmentConfig`, default `DevelopmentConfig`). `DevelopmentConfig` falls back to local `sqlite:///database.db` if `DATABASE_URL` isn't set; prod/staging use Postgres (`postgresql+psycopg2`, rewritten from Heroku's `postgres://` scheme).

**No forms library** — routes read `request.form.get(...)` directly; there is no `forms.py`/Flask-WTF.

### Data model (`app/models.py`)
- `User` — auth (Flask-Login `UserMixin`), owns locations/reports/notifications.
- `Location` — a pantry: address, lat/long, plus an email-only submission flow (`submitter_email`, `verification_token`, `verified`, `verified_at`) that lets non-account-holders register a pantry.
- `Report` — a fullness report: `pantry_fullness`, optional photo, `vision_analysis` (JSON blob) with accessor methods (`get_status()`, `get_detected_food_items()`, `get_ai_fullness_estimate()`, `get_organization_score()`).
- `Notification` — email subscription join (`User`↔`Location`) with a per-subscription `unsubscribe_token` used by the one-click `/unsubscribe/<token>` route.

### AI photo analysis (`app/vision.py`)
Hybrid pipeline: Gemini (`google-generativeai`, primary) with Google Cloud Vision API as fallback, invoked when a report photo is submitted. Results are stored as JSON on `Report.vision_analysis`. Needs `GOOGLE_API_KEY` (Gemini) and `GOOGLE_APPLICATION_CREDENTIALS` (Vision API service account — the JSON key file lives at repo root, gitignored).

### Email (`app/helpers.py: send_email()`)
Flask-Mail over SMTP for every environment: Brevo (`smtp-relay.brevo.com`, the config default) in prod/staging, Mailtrap in dev via `.env`. Sender comes from `MAIL_DEFAULT_SENDER` (default `info@reportthatpantry.org`), supports attachments. Never raises: failures are logged at ERROR with a traceback (`EMAIL SEND FAILED` / `EMAIL NOT SENT` in Heroku logs) and it returns `False`. SendGrid was dropped after its free plan was retired in 2025; `sendgrid` is still imported (unused) in `auth.py`. Used for password reset, empty-pantry notifications, location-verification emails, and QR-poster PDF delivery.

### File uploads
Production photo storage is **S3** (`upload_photo_to_s3`/`delete_photo_from_s3` in `app/helpers.py`, boto3, `S3_BUCKET`/`S3_KEY`/`S3_SECRET`), with HEIC→JPEG conversion via `pillow-heif`. `instance/uploads/` holds leftover files from an earlier pre-S3 version of the upload flow.

### QR poster generation
`generate_qr_poster_pdf()` in `app/helpers.py` (qrcode + reportlab) builds a branded letter-size PDF with a QR code linking to the pantry's report page. Triggered from `views.verify_location()` after email verification and sent as an email attachment — this is what produced the `pantry_qr_poster_*.pdf` files sitting at repo root.

### Templates
Jinja2, mostly extending `app/templates/base-new.html`. The template/route set is mid-redesign: several pages have `-new`/`-old`/`-original` duplicates (`index.html` vs `index-new.html`, `map.html`/`map-new.html`/`map-old.html`, `home` vs `home-old`, `report.html`/`report-demo.html`/`report-original.html`). When editing one of these, check which variant the live route actually renders before assuming the "old" one is dead.

### Not part of the running app
- `pantry_data/` (repo root, untracked) — an offline ML training/dataset dump (`production/train/*.jpg` + `labels.csv`) and env-scoped copies of report photos pulled down for local model work. Not referenced anywhere in `app/`; safe to ignore unless a task is specifically about the ML training workflow.
- `ml-venv/`, `new_venv/` — stray virtualenvs alongside the canonical `venv/`.

## Environment variables

Set in `.env` (gitignored) locally; on Heroku via config vars. Names only:

| Var | Purpose |
|---|---|
| `SECRET_KEY` | Flask session secret |
| `DATABASE_URL` | Postgres connection string |
| `FLASK_ENV` | `production` / `staging` / `development` — selects config class |
| `GOOGLE_MAPS_API_KEY` | Maps JS (add/edit location, map, burrito-brigade pages) |
| `GOOGLE_API_KEY` | Gemini (primary vision analysis) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service-account JSON (Vision API fallback) |
| `CENSUS_API_KEY` | US Census ACS median-income lookup (Burrito Brigade heatmap) |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` | Flask-Mail SMTP: Brevo SMTP login + SMTP key in prod/staging, Mailtrap in dev |
| `S3_BUCKET`, `S3_KEY`, `S3_SECRET` | Photo upload storage |

`LANGCHAIN_API_KEY`/`LANGCHAIN_TRACING_V2` are present in `.env` but unused in `app/` — vestigial from earlier experimentation.

## Stack notes

Pinned to an old stack (Flask 1.1.2, Werkzeug 1.0.1, Jinja2 2.11.3) despite running on Python 3.12.4 (`runtime.txt`) — don't assume Flask 2/3 APIs or behavior are available when writing or debugging code here.
