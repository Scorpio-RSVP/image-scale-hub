#!/bin/bash

# ============================================
# IMAGE RESIZER PRO - UNINSTALL SCRIPT
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Find app directory
if [ -f "/opt/image-resizer-pro/INSTALL_INFO.txt" ]; then
    APP_DIR="/opt/image-resizer-pro"
elif [ -f "/opt/image-resizer/INSTALL_INFO.txt" ]; then
    APP_DIR="/opt/image-resizer"
else
    APP_DIR=$(find /opt -name "INSTALL_INFO.txt" -exec dirname {} \; 2>/dev/null | head -1)
    APP_DIR=${APP_DIR:-"/opt/image-resizer"}
fi

# Get container name
if [ -f "$APP_DIR/INSTALL_INFO.txt" ]; then
    CONTAINER_NAME=$(grep "Container:" "$APP_DIR/INSTALL_INFO.txt" | cut -d: -f2 | tr -d ' ')
    APP_NAME=$(grep "App Name:" "$APP_DIR/INSTALL_INFO.txt" | cut -d: -f2 | xargs)
fi
CONTAINER_NAME=${CONTAINER_NAME:-"image-resizer"}
APP_NAME=${APP_NAME:-"Image Scale Hub"}

echo -e "${RED}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║     ⚠️  $APP_NAME - UNINSTALLER                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}This will remove:${NC}"
echo "  - Docker container ($CONTAINER_NAME)"
echo "  - Docker image ($CONTAINER_NAME)"
echo "  - Nginx configuration"
echo "  - SSL certificates (if installed)"
echo ""
echo -e "${RED}⚠️  Your data in $APP_DIR will be preserved${NC}"
echo ""

read -p "Are you sure you want to uninstall? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}🗑️  Removing Docker container...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true
echo -e "${GREEN}✓ Container removed${NC}"

read -p "Remove Docker image? (y/n): " REMOVE_IMAGE
if [ "$REMOVE_IMAGE" = "y" ]; then
    docker rmi $CONTAINER_NAME 2>/dev/null || true
    echo -e "${GREEN}✓ Image removed${NC}"
fi

echo -e "${YELLOW}🗑️  Removing Nginx configuration...${NC}"
rm -f /etc/nginx/sites-enabled/$CONTAINER_NAME
rm -f /etc/nginx/sites-available/$CONTAINER_NAME
systemctl reload nginx 2>/dev/null || true
echo -e "${GREEN}✓ Nginx config removed${NC}"

read -p "Remove app directory ($APP_DIR)? This deletes ALL DATA! (yes/no): " REMOVE_DATA
if [ "$REMOVE_DATA" = "yes" ]; then
    rm -rf $APP_DIR
    echo -e "${GREEN}✓ App directory removed${NC}"
else
    echo -e "${YELLOW}Data preserved at: $APP_DIR${NC}"
fi

echo ""
echo -e "${GREEN}✅ Uninstall complete!${NC}"
