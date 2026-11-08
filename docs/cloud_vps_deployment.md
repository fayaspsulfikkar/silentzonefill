# Cloud VPS Deployment Guide — Silent Zone Registration Bot

This guide walks you through deploying the Silent Zone Bot to any Linux Cloud VPS (DigitalOcean, Hetzner, AWS, Oracle Cloud, Linode, Google Cloud) so it runs 24/7 independently of your laptop and phone.

---

## 1. Recommended VPS Specs & Region

- **Specs:** 1 vCPU, 1 GB to 2 GB RAM, 15 GB SSD (Ubuntu 22.04 LTS or 24.04 LTS recommended).
- **Region:** **India (Mumbai / Bangalore / Asia-South1)**.
  > ⚡ *Speed Advantage:* Hosting the bot on an Indian VPS reduces the network round-trip time to Google Forms servers to **~5–15 milliseconds**, saving crucial seconds during the 30-second registration window.
- **Cost:**
  - **Oracle Cloud:** Free Tier (Always Free ARM/x86 VM in Mumbai or Hyderabad).
  - **Hetzner:** ~€3.50 / month.
  - **DigitalOcean / Linode:** ~$4–$6 / month.

---

## 2. One-Command Deployment

Once logged into your VPS via SSH (`ssh root@YOUR_SERVER_IP`):

### Step A: Clone the project
```bash
git clone https://github.com/YOUR_USERNAME/SilentZoneFiller.git
cd SilentZoneFiller
```

### Step B: Configure `.env`
```bash
cp .env.example .env
nano .env
```
Fill in your personal information and secrets:
```ini
APP_SECRET_KEY=generate-a-random-hex-string
WEBHOOK_SECRET=your-secret-token

REG_NAME=Your Full Name
REG_PHONE=9876543210
REG_EMAIL=user@example.com
REG_BATCH=BCK-416
REG_RULES_AGREEMENT=YES
REG_COORDINATOR=NO

DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your-secure-password
```

### Step C: Run the Deployment Script
```bash
./deploy.sh
```

The script will automatically:
1. Check / install Docker & Docker Compose.
2. Build the optimized Python 3.12 + Playwright Chromium container.
3. Start the container with restart policies (`restart: unless-stopped`).
4. Validate the healthcheck at `http://localhost:8000/health`.

---

## 3. Free HTTPS Setup (Optional Domain + Let's Encrypt)

If you have a domain name (e.g. `bot.yourdomain.com` pointing to your VPS IP), enable free SSL with Nginx and Certbot in 2 minutes:

### 1. Install Nginx & Certbot
```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
```

### 2. Configure Nginx Proxy
Create `/etc/nginx/sites-available/silentzone`:
```nginx
server {
    server_name bot.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Enable Site & Generate Free SSL Certificate
```bash
sudo ln -s /etc/nginx/sites-available/silentzone /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d bot.yourdomain.com
```

Now your bot has an official, permanent HTTPS URL:
- **Webhook:** `https://bot.yourdomain.com/api/registration/announcement`
- **Dashboard:** `https://bot.yourdomain.com/`

---

## 4. Useful Operations Commands

| Action | Command |
|---|---|
| **View Live Logs** | `docker compose logs -f silentzone` |
| **Restart Service** | `docker compose restart silentzone` |
| **Stop Service** | `docker compose down` |
| **Update Code & Rebuild** | `git pull && ./deploy.sh` |
| **Check SQLite Database** | `docker compose exec silentzone sqlite3 data/silentzone.db "SELECT * FROM registration_attempts;"` |
| **View Error Screenshots** | Screenshots are mounted on the host in `./screenshots/` |

