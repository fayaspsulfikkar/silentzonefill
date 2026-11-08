#!/usr/bin/env bash
# ==============================================================================
# Silent Zone Automation — Production Deployment Script for AWS EC2 & Linux VPS
# Target OS: Ubuntu 24.04 LTS / Debian 12 / Ubuntu 22.04 LTS
# Usage: ./deploy.sh
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}    Silent Zone Registration Bot — Deployment Script   ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Determine sudo capability
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo &>/dev/null; then
        SUDO="sudo"
    else
        echo -e "${RED}[✗] Sudo is required for non-root users.${NC}"
        exit 1
    fi
fi

# 2. Check and install Docker if missing
if ! command -v docker &>/dev/null; then
    echo -e "${YELLOW}[!] Docker not found. Installing official Docker engine...${NC}"
    $SUDO apt-get update -y
    $SUDO apt-get install -y ca-certificates curl gnupg
    $SUDO install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg || true
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg || true

    # Fallback to get.docker.com if distro apt repo differs
    if ! curl -fsSL https://get.docker.com -o get-docker.sh; then
        echo -e "${RED}[✗] Failed to download Docker installer.${NC}"
        exit 1
    fi
    $SUDO sh get-docker.sh
    rm -f get-docker.sh
    $SUDO systemctl enable --now docker
    echo -e "${GREEN}[✓] Docker installed and started.${NC}"
fi

# Ensure user is part of docker group
if [ -n "${USER:-}" ] && [ "$(id -u)" -ne 0 ]; then
    $SUDO usermod -aG docker "$USER" 2>/dev/null || true
fi

# 3. Determine working Docker & Docker Compose commands (handles group permissions)
DOCKER_CMD="docker"
if ! docker info &>/dev/null; then
    if $SUDO docker info &>/dev/null; then
        DOCKER_CMD="$SUDO docker"
        echo -e "${YELLOW}[!] Notice: Running Docker with sudo (group permissions pending shell restart).${NC}"
    else
        echo -e "${RED}[✗] Docker daemon is not running or accessible.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}[✓] Docker is ready: $($DOCKER_CMD --version)${NC}"

COMPOSE_CMD=""
if $DOCKER_CMD compose version &>/dev/null; then
    COMPOSE_CMD="$DOCKER_CMD compose"
elif command -v docker-compose &>/dev/null && $SUDO docker-compose version &>/dev/null; then
    COMPOSE_CMD="$SUDO docker-compose"
else
    echo -e "${YELLOW}[!] Docker Compose plugin not found. Installing docker-compose-plugin...${NC}"
    $SUDO apt-get update -y && $SUDO apt-get install -y docker-compose-plugin
    COMPOSE_CMD="$DOCKER_CMD compose"
fi
echo -e "${GREEN}[✓] Docker Compose is ready: $($COMPOSE_CMD version)${NC}"

# 4. Check for .env file and validate credentials
if [ ! -f .env ]; then
    echo -e "${YELLOW}[!] .env file not found! Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}[✗] Created .env from template. Please configure your .env before deploying!${NC}"
    exit 1
fi

# Security check: Reject default placeholder credentials
if grep -q "change-me-to-another-long-random-string" .env 2>/dev/null || \
   grep -q "WEBHOOK_SECRET=change-me" .env 2>/dev/null || \
   grep -q "DASHBOARD_PASSWORD=change-me" .env 2>/dev/null; then
    echo -e "${RED}======================================================${NC}"
    echo -e "${RED}[✗] SECURITY ERROR: Default placeholder credentials detected!${NC}"
    echo -e "${RED}    You must change WEBHOOK_SECRET and DASHBOARD_PASSWORD in .env.${NC}"
    echo -e "${RED}======================================================${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] .env file validated.${NC}"

# 5. Prepare host directories with secure permissions (least privilege, no chmod 777)
mkdir -p data screenshots
chmod 750 data screenshots
echo -e "${GREEN}[✓] Persistent directories configured (data/, screenshots/).${NC}"

# 6. Build and launch container
echo -e "${BLUE}[*] Building and starting Silent Zone container...${NC}"
$COMPOSE_CMD up -d --build

# 7. Wait for health check (queried locally on 127.0.0.1:8000)
echo -e "${BLUE}[*] Waiting for container health check on http://127.0.0.1:8000/health...${NC}"
HEALTHY=false
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health | grep -q '"status":"ok"'; then
        HEALTHY=true
        break
    fi
    sleep 1
done

if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}======================================================${NC}"
    echo -e "${GREEN}  ✓ SILENT ZONE BOT IS RUNNING AND HEALTHY!           ${NC}"
    echo -e "${GREEN}======================================================${NC}"
    echo -e "Internal Binding:  http://127.0.0.1:8000 (Protected from public internet)"
    echo -e "Public Access:     Configure Nginx reverse proxy on port 443 with SSL"
    echo -e "SSH Tunnel Access: ssh -L 8000:127.0.0.1:8000 <user>@<ec2-ip>"
    echo -e "Live Logs:         $COMPOSE_CMD logs -f silentzone"
    echo -e "Stop Service:      $COMPOSE_CMD down"
else
    echo -e "${RED}[✗] Health check timed out. Showing recent container logs:${NC}"
    $COMPOSE_CMD logs --tail=50 silentzone
    exit 1
fi
