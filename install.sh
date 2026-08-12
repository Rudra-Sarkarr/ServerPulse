#!/usr/bin/env bash
# ==============================================================================
# ⚡ SERVERPULSE & DISCORD BOT - PTERODACTYL STYLE 1-CLICK INTERACTIVE INSTALLER
# ==============================================================================
# Usage:
#   bash <(curl -sSL https://raw.githubusercontent.com/Rudra-Sarkarr/ServerPulse/main/install.sh)
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${CYAN}${BOLD}"
echo "====================================================================="
echo "   ⚡ SERVERPULSE & DISCORD BOT - PTERODACTYL STYLE INSTALLER"
echo "====================================================================="
echo -e "${NC}"

# Check root privileges
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ Error: You must run this installation script as root!${NC}"
  echo "Please switch to root user using 'sudo su' or 'su root' and run again."
  exit 1
fi

prompt_input() {
  local prompt_msg="$1"
  local var_name="$2"
  local default_val="$3"
  
  if [ -c /dev/tty ]; then
    read -p "$prompt_msg" $var_name </dev/tty
  else
    read -p "$prompt_msg" $var_name
  fi

  if [ -z "${!var_name}" ] && [ -n "$default_val" ]; then
    eval "$var_name=\"$default_val\""
  fi
}

echo -e "${YELLOW}Please answer the setup questions below:${NC}\n"

# 1. Ask for Discord Bot Token
BOT_TOKEN=""
while [ -z "$BOT_TOKEN" ]; do
  prompt_input "🔑 Enter your Discord Bot Token: " BOT_TOKEN ""
  if [ -z "$BOT_TOKEN" ]; then
    echo -e "${RED}Bot Token cannot be empty! Please try again.${NC}"
  fi
done

# 2. Ask for Discord SERVER (GUILD) ID (Replaces manual Channel ID!)
GUILD_ID=""
prompt_input "🏰 Enter your Discord Server (Guild) ID: " GUILD_ID ""

# 3. Choose Access Mode: VPS IP or Custom Domain
echo -e "\n${CYAN}=====================================================================${NC}"
echo -e "${BOLD}🌐 SELECT WEB DASHBOARD ACCESS MODE:${NC}"
echo -e "  [1] Direct VPS IP Mode  (e.g., http://YOUR-VPS-IP:8080)"
echo -e "  [2] Custom Domain Mode  (e.g., https://status.yourdomain.com with SSL)"
echo -e "${CYAN}=====================================================================${NC}"

prompt_input "Select Option [1 or 2, Default: 1]: " ACCESS_MODE "1"

DOMAIN_NAME=""
SSL_EMAIL=""
WEB_PORT="8080"

if [ "$ACCESS_MODE" == "2" ]; then
  while [ -z "$DOMAIN_NAME" ]; do
    prompt_input "🌐 Enter your Domain Name (e.g. status.myvps.com): " DOMAIN_NAME ""
  done
  prompt_input "📧 Enter Email for free SSL Certificate (Let's Encrypt): " SSL_EMAIL ""
else
  prompt_input "🌐 Enter Web Dashboard Port [Default: 8080]: " INPUT_PORT "8080"
  WEB_PORT=${INPUT_PORT:-8080}
fi

REFRESH_INTERVAL=2

echo -e "\n${CYAN}---------------------------------------------------------------------${NC}"
echo -e "${GREEN}✅ Installation Summary:${NC}"
echo -e " • Bot Token:          ${CYAN}${BOT_TOKEN:0:18}...${NC}"
echo -e " • Server (Guild) ID:  ${CYAN}${GUILD_ID:-Auto-detect}${NC}"
echo -e " • Access Mode:        ${CYAN}$([ "$ACCESS_MODE" == "2" ] && echo "Custom Domain ($DOMAIN_NAME)" || echo "VPS IP (Port $WEB_PORT)")${NC}"
echo -e " • Refresh Interval:   ${CYAN}2 seconds (Real-Time)${NC}"
echo -e "${CYAN}---------------------------------------------------------------------${NC}\n"

prompt_input "Proceed with installation on this server? (y/n) [Default: y]: " CONFIRM "y"
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo -e "${RED}Installation cancelled by user.${NC}"
  exit 0
fi

# Step 1: Install Dependencies
echo -e "\n${YELLOW}📦 [1/5] Installing system packages (Python3, venv, git, curl, nginx)...${NC}"
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl nginx certbot python3-certbot-nginx

# Step 2: Prepare Application Directory
INSTALL_DIR="/opt/vps-monitor-bot"
echo -e "${YELLOW}📂 [2/5] Setting up project directory at ${INSTALL_DIR}...${NC}"
mkdir -p "$INSTALL_DIR"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" 2>/dev/null && pwd || echo "" )"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/bot.py" ]; then
  cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR"/ 2>/dev/null || true
fi

cd "$INSTALL_DIR"

if [ ! -f "$INSTALL_DIR/bot.py" ]; then
  echo -e "${YELLOW}📥 Fetching application source code from repository...${NC}"
  git clone https://github.com/Rudra-Sarkarr/ServerPulse.git "$INSTALL_DIR" 2>/dev/null || true
fi

# Step 3: Python Environment
echo -e "${YELLOW}🐍 [3/5] Setting up Python virtual environment...${NC}"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/venv/bin/pip" install discord.py psutil python-dotenv tabulate --quiet

# Step 4: Write Environment Config
echo -e "${YELLOW}⚙️ [4/5] Generating .env configuration file...${NC}"
cat <<EOF > "$INSTALL_DIR/.env"
DISCORD_TOKEN=${BOT_TOKEN}
GUILD_ID=${GUILD_ID}
MONITOR_CHANNEL_ID=
ALERT_CHANNEL_ID=
REFRESH_INTERVAL=${REFRESH_INTERVAL}
CPU_ALERT_THRESHOLD=85
RAM_ALERT_THRESHOLD=85
DISK_ALERT_THRESHOLD=90
ALERT_COOLDOWN=300
WEB_HOST=0.0.0.0
WEB_PORT=${WEB_PORT}
DOMAIN_NAME=${DOMAIN_NAME}
USE_DOMAIN=$([ "$ACCESS_MODE" == "2" ] && echo "true" || echo "false")
EOF

chmod 600 "$INSTALL_DIR/.env"

# Step 5: Domain Nginx SSL Setup (If Option 2 selected)
if [ "$ACCESS_MODE" == "2" ] && [ -n "$DOMAIN_NAME" ]; then
  echo -e "${YELLOW}🔒 Setting up Nginx Reverse Proxy & Let's Encrypt SSL for ${DOMAIN_NAME}...${NC}"
  cat <<EOF > "/etc/nginx/sites-available/serverpulse"
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    location / {
        proxy_pass http://127.0.0.1:${WEB_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
  ln -sf /etc/nginx/sites-available/serverpulse /etc/nginx/sites-enabled/
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx

  if [ -n "$SSL_EMAIL" ]; then
    certbot --nginx -d "$DOMAIN_NAME" --non-interactive --agree-tos -m "$SSL_EMAIL" || echo "SSL setup can be completed later using certbot --nginx -d $DOMAIN_NAME"
  fi
fi

# Step 6: Systemd Background Service
echo -e "${YELLOW}🚀 [5/5] Enabling 24/7 background systemd service...${NC}"
cat <<EOF > /etc/systemd/system/vps-monitor-bot.service
[Unit]
Description=VPS Real-Time Resource Monitoring Discord Bot & ServerPulse Web Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now vps-monitor-bot.service

VPS_IP=$(curl -s --max-time 5 ifconfig.me || curl -s --max-time 5 icanhazip.com || echo "YOUR-VPS-IP")

echo -e "\n${GREEN}${BOLD}"
echo "====================================================================="
echo " 🎉 INSTALLATION SUCCESSFUL! BOT & DASHBOARD ARE LIVE 24/7"
echo "====================================================================="
echo -e "${NC}"
echo -e "🤖 ${BOLD}Discord Bot:${NC}      Connected & Active"
if [ "$ACCESS_MODE" == "2" ]; then
  echo -e "🌐 ${BOLD}Web Dashboard:${NC}    ${CYAN}https://${DOMAIN_NAME}${NC}"
else
  echo -e "🌐 ${BOLD}Web Dashboard:${NC}    ${CYAN}http://${VPS_IP}:${WEB_PORT}${NC}"
fi
echo -e "📂 ${BOLD}Directory:${NC}        ${INSTALL_DIR}"
echo -e ""
echo -e "${YELLOW}Useful Service Commands:${NC}"
echo -e " • Check Status: ${CYAN}systemctl status vps-monitor-bot${NC}"
echo -e " • View Logs:     ${CYAN}journalctl -u vps-monitor-bot -f${NC}"
echo -e " • Restart:       ${CYAN}systemctl restart vps-monitor-bot${NC}"
echo -e " • Edit Config:   ${CYAN}nano ${INSTALL_DIR}/.env${NC}"
echo "====================================================================="
