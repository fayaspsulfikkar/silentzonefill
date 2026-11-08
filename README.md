# Silent Zone Registration Automation

A reliable, high-speed registration automation system for the institute's monthly Silent Zone programme.

## Architecture

```
WhatsApp Announcement (Phone locked)
       │
       ▼
Android Listener (MacroDroid / Tasker)
       │ Extracts Google Forms URL
       ▼ HTTPS POST + Secret Header
Cloud Server (FastAPI on VPS)
       │ URL validation & SHA-256 deduplication
       ▼
Playwright Chromium Worker (Pre-warmed)
       │ Container-scoped field matching (Name, Phone, Batch, Rules, Coordinator)
       ▼
Google Forms Submission & Confirmation Page Verification
       │
       ▼
Telegram Notification + Audit Log (SQLite)
```

---

## Quick Start (Local Development)

```bash
# 1. Enter the project directory
cd SilentZoneFiller

# 2. Create virtual environment & activate
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies & Chromium
pip install -r requirements.txt
playwright install chromium

# 4. Configure environment (NEVER commit .env)
cp .env.example .env
# Edit .env with your details

# 5. Run development server
uvicorn app.main:app --port 8000
```

- **Web Dashboard:** `http://localhost:8000/` (Protected with HTTP Basic Auth)
- **API Documentation:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

---

## Android Phone Integration

Choose either option depending on your preference:

1. **[Free MacroDroid Setup Guide](android/macrodroid_setup.md)** *(100% Free on Google Play, no purchase required).*
2. **[Tasker + AutoNotification Setup Guide](android/tasker_setup.md)** *(For existing Tasker users).*

Both guides include the 4 anti-kill settings to ensure the listener stays active while your phone screen is locked.

---

## Cloud VPS Deployment

Deploying to a Linux VPS (DigitalOcean, Hetzner, AWS, Oracle Cloud Free Tier) runs the bot 24/7 independently of your laptop.

### One-Command Deployment
```bash
./deploy.sh
```

For full VPS setup instructions, region recommendations (Mumbai / India for 5–15ms latency), and free Let's Encrypt SSL with Nginx, see **[Cloud VPS Deployment Guide](docs/cloud_vps_deployment.md)**.

---

## Running Tests

```bash
# Run all 43 unit, security validation, and mock tests
pytest tests/ -m "not live" -v

# Run live test against your Google Form
pytest tests/test_live_form.py -v
```

---

## Project Structure

```
SilentZoneFiller/
├── app/
│   ├── api/             # FastAPI route handlers (webhook, manual, status, dashboard)
│   ├── automation/      # Playwright browser, detector, container-scoped filler, submitter, orchestrator
│   ├── services/        # Announcement validation, registration state machine, Telegram notifier
│   ├── database/        # SQLAlchemy async engine, SQLite schema, registration attempt models
│   ├── config.py        # Pydantic Settings (zero hardcoding, runtime env loading)
│   ├── dependencies.py  # HTTP Basic Auth guards
│   └── main.py          # FastAPI app factory & browser lifespan
├── android/
│   ├── macrodroid_setup.md  # 100% Free Android setup guide
│   └── tasker_setup.md      # Tasker + AutoNotification setup guide
├── dashboard/
│   └── templates/       # Jinja2 dashboard templates with 3s live auto-refresh
├── docs/
│   └── cloud_vps_deployment.md  # Complete VPS & Nginx SSL deployment guide
├── tests/               # 35 comprehensive unit, mock, and live integration tests
├── Dockerfile           # Optimized Python 3.12 + Playwright Chromium container
├── docker-compose.yml   # Multi-service compose with persistent storage & healthchecks
├── deploy.sh            # Automated one-click VPS deployment script
├── .env.example         # Template environment variables (no PII)
├── .gitignore           # Strictly ignores .env, data/, screenshots/, binaries
└── README.md
```

---

## Security & Privacy Compliance

- **Zero Hardcoded PII:** Personal details (`REG_NAME`, `REG_PHONE`, `REG_BATCH`, etc.) are loaded exclusively via environment variables.
- **Git Protection:** `.gitignore` blocks `.env`, database files (`data/`), screenshots, and virtual environments from version control.
- **Log Sanitation:** Phone numbers are excluded from application logs.
- **Idempotency:** SHA-256 hash deduplication guarantees a form is never submitted twice.

---

## Phase Progress: 100% Complete

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Architecture, data model, security boundaries | ✅ Complete |
| **Phase 2** | Playwright form automation & DOM reverse-engineering | ✅ Complete |
| **Phase 3** | Live testing against controlled Google Form | ✅ Complete |
| **Phase 4** | FastAPI backend, webhook, deduplication, state machine | ✅ Complete |
| **Phase 5** | Android notification forwarding (MacroDroid & Tasker) | ✅ Complete |
| **Phase 6** | Real-time web dashboard & Telegram push notifications | ✅ Complete |
| **Phase 7** | Docker containerization, `deploy.sh`, and VPS guide | ✅ Complete |
| **Phase 8** | End-to-end testing & audit (35/35 tests passing) | ✅ Complete |
