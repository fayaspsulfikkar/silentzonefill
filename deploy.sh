#!/usr/bin/env bash
# ==============================================================================
# Silent Zone Automation — One-Click Production Deployment Script
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

# 1. Check Docker installation
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}[!] Docker not found. Installing Docker using get.docker.com...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker "$USER" || true
    rm -f get-docker.sh
    echo -e "${GREEN}[✓] Docker installed successfully.${NC}"
else
    echo -e "${GREEN}[✓] Docker is installed: $(docker --version)${NC}"
fi

# 2. Check Docker Compose
DOCKER_COMPOSE_CMD=""
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}[✗] Docker Compose plugin is required. Please install docker-compose-plugin.${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] Docker Compose found: $($DOCKER_COMPOSE_CMD version)${NC}"

# 3. Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}[!] .env file not found! Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}[!] Created .env from template. Please edit .env with your details before starting!${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] .env file is present.${NC}"

# 4. Prepare host directories
mkdir -p data screenshots
chmod 777 data screenshots || true

# 5. Build and launch container
echo -e "${BLUE}[*] Building and launching Silent Zone container...${NC}"
$DOCKER_COMPOSE_CMD up -d --build

# 6. Wait for health check
echo -e "${BLUE}[*] Waiting for container health check...${NC}"
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
    echo -e "Dashboard:      http://YOUR_SERVER_IP:8000/"
    echo -e "Webhook:        http://YOUR_SERVER_IP:8000/api/registration/announcement"
    echo -e "Live Logs:      $DOCKER_COMPOSE_CMD logs -f silentzone"
    echo -e "Stop Service:   $DOCKER_COMPOSE_CMD down"
else
    echo -e "${RED}[✗] Health check timed out. Showing recent container logs:${NC}"
    $DOCKER_COMPOSE_CMD logs --tail=50 silentzone
    exit 1
fi

