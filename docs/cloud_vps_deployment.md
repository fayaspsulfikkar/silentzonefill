# AWS EC2 Deployment Guide — Silent Zone Registration Bot
### Target OS: Ubuntu 24.04 LTS (Noble Numbat) on AWS EC2

This guide walks you through deploying the Silent Zone Bot to an **AWS EC2** instance running **Ubuntu 24.04 LTS** so it operates 24/7 independently of your laptop and phone.

---

## 1. AWS EC2 Instance Specs & Region

- **Recommended Instance Type:**
  - `t3.small` (x86_64) or `t4g.small` (ARM64) — **2 vCPUs, 2 GB RAM**.
  - *Free Tier Alternative:* `t3.micro` or `t2.micro` (1 GB RAM). If using 1 GB RAM, configure a **2 GB swap file** (detailed below) so Chromium never encounters Out-Of-Memory issues.
- **Recommended Region:**
  - **ap-south-1 (Mumbai)** or **ap-south-2 (Hyderabad)**.
  - ⚡ *Speed Advantage:* Hosting on an Indian AWS region drops network latency to Google Forms servers to **~5–15 milliseconds**, giving you the fastest possible submission during the 30-second window.
- **Storage:** 20 GB gp3 SSD.

---

## 2. AWS Security Group Configuration (Crucial)

Configure the EC2 Inbound Rules in the AWS Console:

| Type | Port Range | Protocol | Source | Purpose |
|---|---|---|---|---|
| **SSH** | 22 | TCP | `My IP` (`x.x.x.x/32`) | Secure server administration |
| **HTTP** | 80 | TCP | `0.0.0.0/0` | Let's Encrypt validation & HTTPS redirect |
| **HTTPS** | 443 | TCP | `0.0.0.0/0` | Secure MacroDroid webhook & Dashboard |

> 🔒 **Security Notice:**
> **DO NOT** add Port 8000 to your AWS Security Group.
> `docker-compose.yml` binds strictly to `127.0.0.1:8000` (loopback only). Port 8000 is never exposed directly to the public internet, and all traffic is routed securely through Nginx on Port 443 with TLS encryption.

---

## 3. Server Setup (Ubuntu 24.04 LTS)

### Step A: Connect to EC2
```bash
ssh -i "your-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

### Step B: System Update & Swap (Mandatory for 1GB Instances)
```bash
sudo apt update && sudo apt upgrade -y

# Create 2GB swap file (prevents Chromium memory spikes)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 4. Deploy the Bot with `./deploy.sh`

### Step A: Clone the Repository
```bash
git clone https://github.com/fayaspsulfikkar/silentzonefill.git
cd silentzonefill
```

### Step B: Configure `.env`
```bash
cp .env.example .env
nano .env
```

Fill in your configuration:
```ini
APP_ENV=production

# Security secrets (generate random strings with: openssl rand -hex 24)
APP_SECRET_KEY=put-a-strong-random-string-at-least-16-chars
WEBHOOK_SECRET=put-a-strong-random-webhook-secret-at-least-16-chars

# Registration credentials
REG_NAME=Your Full Name
REG_PHONE=9876543210
REG_EMAIL=user@example.com
REG_BATCH=BCK-416
REG_RULES_AGREEMENT=YES
REG_COORDINATOR=NO

# Dashboard authentication (min 8 chars, default passwords rejected in production)
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your-secure-dashboard-password

# Optional Telegram notifications
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

DATABASE_URL=sqlite+aiosqlite:///./data/silentzone.db
BROWSER_HEADLESS=true
BROWSER_TIMEOUT_MS=30000
ALLOWED_FORM_DOMAINS=docs.google.com,forms.gle
```

> ⚠️ **Production Credential Validation:**
> In production mode (`APP_ENV=production`), the application will immediately abort startup if `DASHBOARD_PASSWORD`, `WEBHOOK_SECRET`, or `APP_SECRET_KEY` are left as default placeholder values (`change-me`).

### Step C: Run Automated Deployment
```bash
./deploy.sh
```

The script automatically:
1. Detects and installs Docker and the Docker Compose plugin on Ubuntu 24.04.
2. Fixes user group permissions so commands run seamlessly.
3. Sets secure directory permissions (`chmod 750` — no insecure `chmod 777`).
4. Builds the container with Playwright Chromium and Debian OS libraries.
5. Binds strictly to `127.0.0.1:8000` and validates the healthcheck.

---

## 5. Nginx Reverse Proxy with Free Let's Encrypt SSL

Point your domain or subdomain (e.g., `silentzone.yourdomain.com`) to your EC2 Public IP via an **A record**, then run:

### 1. Install Nginx and Certbot
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 2. Configure Nginx Proxy
Create `/etc/nginx/sites-available/silentzone`:
```nginx
server {
    server_name silentzone.yourdomain.com;

    # Maximum upload size for diagnostic logs
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Enable Site and Obtain SSL Certificate
```bash
sudo ln -s /etc/nginx/sites-available/silentzone /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d silentzone.yourdomain.com
```

Certbot will automatically obtain a free SSL certificate and configure automatic HTTPS renewals.

Your bot is now live at:
- **Webhook Endpoint:** `https://silentzone.yourdomain.com/api/registration/announcement`
- **Dashboard:** `https://silentzone.yourdomain.com/`

---

## 6. Alternative: Access Without Domain (SSH Tunnel)

If you do not have a domain name, you can securely access the web dashboard from your local computer via an SSH tunnel:

```bash
# Run this on your local laptop:
ssh -i "your-key.pem" -L 8000:127.0.0.1:8000 ubuntu@<YOUR_EC2_PUBLIC_IP>
```
Then open your laptop browser to `http://localhost:8000/`.

---

## 7. Data Persistence & Operations

| Action | Command | Details |
|---|---|---|
| **View Live Logs** | `docker compose logs -f silentzone` | Follow live container logs |
| **Check SQLite Database** | `docker compose exec silentzone sqlite3 data/silentzone.db "SELECT * FROM registration_attempts;"` | Audits stored in `./data/silentzone.db` |
| **View Error Screenshots** | Host path: `./screenshots/` | Persists across container restarts |
| **Restart Service** | `docker compose restart silentzone` | Zero downtime restarts |
| **Update Code & Rebuild** | `git pull && ./deploy.sh` | Pulls latest changes, rebuilds container, retains all DB data |
| **Stop Service** | `docker compose down` | Stops container (volumes in `./data` remain intact) |
