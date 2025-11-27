#!/bin/bash

# ============================================
# IMAGE RESIZER PRO - INSTALLATION SCRIPT
# ============================================
# This script sets up the complete application with:
# - Docker container
# - Nginx reverse proxy
# - Free SSL certificate (Let's Encrypt)
# - Auto-renewal
# - Custom branding
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║     🖼️  IMAGE RESIZER PRO - INSTALLER                 ║"
echo "║     Professional Image Processing Tool                 ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Get installation options
echo -e "${YELLOW}📋 Installation Options${NC}"
echo ""

# App name/branding
read -p "Enter your app name (e.g., My Image Tool): " APP_NAME
APP_NAME=${APP_NAME:-"Image Scale Hub"}
echo -e "${GREEN}✓ App will be branded as: $APP_NAME${NC}"
echo ""

# Domain setup
read -p "Do you want to set up a custom domain? (y/n): " USE_DOMAIN
if [ "$USE_DOMAIN" = "y" ] || [ "$USE_DOMAIN" = "Y" ]; then
    read -p "Enter your domain (e.g., images.example.com): " DOMAIN
    read -p "Set up free SSL certificate? (y/n): " USE_SSL
    
    # Validate domain is pointing to this server
    echo -e "${YELLOW}⚠️  Make sure your domain's DNS A record points to this server's IP${NC}"
    read -p "Press Enter when DNS is configured, or Ctrl+C to cancel..."
fi

# Port selection
read -p "Enter port for the app (default: 5000): " APP_PORT
APP_PORT=${APP_PORT:-5000}

# Admin credentials
echo ""
echo -e "${YELLOW}🔐 Admin Account Setup${NC}"
read -p "Admin username (default: admin): " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}
read -s -p "Admin password (default: admin123): " ADMIN_PASS
ADMIN_PASS=${ADMIN_PASS:-admin123}
echo ""

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)

echo ""
echo -e "${BLUE}📦 Installing dependencies...${NC}"

# Update system
apt-get update -qq

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Install Nginx if using domain
if [ "$USE_DOMAIN" = "y" ] || [ "$USE_DOMAIN" = "Y" ]; then
    if ! command -v nginx &> /dev/null; then
        echo -e "${YELLOW}Installing Nginx...${NC}"
        apt-get install -y nginx
        systemctl enable nginx
        echo -e "${GREEN}✓ Nginx installed${NC}"
    else
        echo -e "${GREEN}✓ Nginx already installed${NC}"
    fi
fi

# Create app directory
# Convert app name to directory-safe format
APP_DIR_NAME=$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
APP_DIR="/opt/${APP_DIR_NAME:-image-resizer}"
mkdir -p $APP_DIR/data
mkdir -p $APP_DIR/static/uploads

echo -e "${BLUE}📝 Creating configuration...${NC}"

# Create .env file
cat > $APP_DIR/.env << EOF
# $APP_NAME Configuration
# Generated on $(date)

SECRET_KEY=$SECRET_KEY
APP_NAME=$APP_NAME
APP_VERSION=1.0.0
FLASK_CONFIG=production

# Database (SQLite default, change for MySQL/PostgreSQL)
DATABASE_URL=sqlite:////app/data/users.db

# Admin
ADMIN_USERNAME=$ADMIN_USER
ADMIN_PASSWORD=$ADMIN_PASS

# Security
SESSION_TIMEOUT=1800
MAX_LOGIN_ATTEMPTS=5

# Storage
MAX_FILE_SIZE=10485760
DEFAULT_STORAGE_LIMIT_MB=100

# Features
ENABLE_REGISTRATION=false
EOF

echo -e "${GREEN}✓ Configuration created${NC}"

# Copy application files (assumes script is run from app directory)
if [ -f "app.py" ]; then
    cp -r . $APP_DIR/
    echo -e "${GREEN}✓ Application files copied${NC}"
fi

# Build and run Docker container
echo -e "${BLUE}🐳 Building Docker container...${NC}"

cd $APP_DIR

# Container name from app name
CONTAINER_NAME=$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
CONTAINER_NAME=${CONTAINER_NAME:-image-resizer}

# Stop existing container if running
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Build image
docker build -t $CONTAINER_NAME . 

# Run container
docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p 127.0.0.1:$APP_PORT:5000 \
    -v $APP_DIR/data:/app/data \
    -v $APP_DIR/static/uploads:/app/static/uploads \
    --env-file $APP_DIR/.env \
    $CONTAINER_NAME

echo -e "${GREEN}✓ Docker container running${NC}"

# Configure Nginx if using domain
if [ "$USE_DOMAIN" = "y" ] || [ "$USE_DOMAIN" = "Y" ]; then
    echo -e "${BLUE}🌐 Configuring Nginx...${NC}"
    
    # Create Nginx config
    cat > /etc/nginx/sites-available/$CONTAINER_NAME << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # File upload size
        client_max_body_size 20M;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/$CONTAINER_NAME /etc/nginx/sites-enabled/
    
    # Remove default site if exists
    rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload Nginx
    nginx -t
    systemctl reload nginx
    
    echo -e "${GREEN}✓ Nginx configured${NC}"
    
    # Set up SSL if requested
    if [ "$USE_SSL" = "y" ] || [ "$USE_SSL" = "Y" ]; then
        echo -e "${BLUE}🔒 Setting up SSL certificate...${NC}"
        
        # Install Certbot
        if ! command -v certbot &> /dev/null; then
            apt-get install -y certbot python3-certbot-nginx
        fi
        
        # Get certificate
        certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect
        
        # Set up auto-renewal
        systemctl enable certbot.timer
        systemctl start certbot.timer
        
        echo -e "${GREEN}✓ SSL certificate installed${NC}"
        echo -e "${GREEN}✓ Auto-renewal enabled${NC}"
    fi
fi

# Final output
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ INSTALLATION COMPLETE!                         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$USE_DOMAIN" = "y" ] || [ "$USE_DOMAIN" = "Y" ]; then
    if [ "$USE_SSL" = "y" ] || [ "$USE_SSL" = "Y" ]; then
        echo -e "🌐 Your app is running at: ${BLUE}https://$DOMAIN${NC}"
    else
        echo -e "🌐 Your app is running at: ${BLUE}http://$DOMAIN${NC}"
    fi
else
    SERVER_IP=$(curl -s ifconfig.me)
    echo -e "🌐 Your app is running at: ${BLUE}http://$SERVER_IP:$APP_PORT${NC}"
fi

echo ""
echo -e "👤 Admin Login:"
echo -e "   Username: ${YELLOW}$ADMIN_USER${NC}"
echo -e "   Password: ${YELLOW}$ADMIN_PASS${NC}"
echo ""
echo -e "📁 App Directory: ${BLUE}$APP_DIR${NC}"
echo -e "📊 Logs: ${BLUE}docker logs $CONTAINER_NAME${NC}"
echo ""
echo -e "${YELLOW}⚠️  Remember to change the default admin password!${NC}"
echo ""

# Save installation info
cat > $APP_DIR/INSTALL_INFO.txt << EOF
$APP_NAME - Installation Info
==========================================
Installed: $(date)
App Name: $APP_NAME
Container: $CONTAINER_NAME
Domain: ${DOMAIN:-"None (IP access)"}
Port: $APP_PORT
SSL: ${USE_SSL:-"No"}
Admin User: $ADMIN_USER
App Directory: $APP_DIR

Commands:
- View logs: docker logs $CONTAINER_NAME
- Restart: docker restart $CONTAINER_NAME
- Stop: docker stop $CONTAINER_NAME
- Update: cd $APP_DIR && docker build -t $CONTAINER_NAME . && docker restart $CONTAINER_NAME
EOF

echo -e "${GREEN}Installation info saved to: $APP_DIR/INSTALL_INFO.txt${NC}"
