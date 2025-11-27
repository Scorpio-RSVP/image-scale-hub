#!/bin/bash

# ============================================
# IMAGE RESIZER PRO - UPDATE SCRIPT
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Find app directory from INSTALL_INFO or use default
if [ -f "/opt/Image Scale Hub/INSTALL_INFO.txt" ]; then
    APP_DIR="/opt/Image Scale Hub"
elif [ -f "/opt/image-resizer/INSTALL_INFO.txt" ]; then
    APP_DIR="/opt/image-resizer"
else
    # Try to find any install
    APP_DIR=$(find /opt -name "INSTALL_INFO.txt" -exec dirname {} \; 2>/dev/null | head -1)
    APP_DIR=${APP_DIR:-"/opt/image-resizer"}
fi

# Get container name from install info
if [ -f "$APP_DIR/INSTALL_INFO.txt" ]; then
    CONTAINER_NAME=$(grep "Container:" "$APP_DIR/INSTALL_INFO.txt" | cut -d: -f2 | tr -d ' ')
fi
CONTAINER_NAME=${CONTAINER_NAME:-"image-resizer"}

echo -e "${BLUE}🔄 Updating $CONTAINER_NAME...${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if app is installed
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}❌ App not found at $APP_DIR${NC}"
    echo "Run install.sh first"
    exit 1
fi

cd $APP_DIR

# Backup database
echo -e "${YELLOW}📦 Backing up database...${NC}"
BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S).db"
cp data/users.db "data/$BACKUP_NAME" 2>/dev/null || true
echo -e "${GREEN}✓ Backup created: $BACKUP_NAME${NC}"

# Pull latest code (if using git)
if [ -d ".git" ]; then
    echo -e "${YELLOW}📥 Pulling latest code...${NC}"
    git pull origin main
fi

# Rebuild Docker image
echo -e "${YELLOW}🐳 Rebuilding Docker image...${NC}"
docker build -t $CONTAINER_NAME .

# Restart container
echo -e "${YELLOW}🔄 Restarting container...${NC}"
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p 127.0.0.1:5000:5000 \
    -v $APP_DIR/data:/app/data \
    -v $APP_DIR/static/uploads:/app/static/uploads \
    --env-file $APP_DIR/.env \
    $CONTAINER_NAME

echo ""
echo -e "${GREEN}✅ Update complete!${NC}"
echo -e "📊 Check logs: ${BLUE}docker logs $CONTAINER_NAME${NC}"
