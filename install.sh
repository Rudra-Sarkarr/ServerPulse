#!/usr/bin/env bash
# ==============================================================================
# ⚡ SERVERPULSE & DISCORD BOT 1-CLICK REMOTE INSTALLER (Pterodactyl Style)
# ==============================================================================
# Usage:
#   bash <(curl -sSL https://raw.githubusercontent.com/your-repo/vps-monitor-bot/main/install.sh)
# ==============================================================================

set -e

# Color Definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

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

# Ensure TTY is available for interactive prompts when piped via curl
if [ ! -t 0 ] && [ ! -c /dev/tty ]; then
  echo -e "${RED}❌ Error: No interactive TTY available for input prompts.${NC}"
  exit 1
fi

# Function to read input safely from /dev/tty
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

# 2. Ask for Live Status Channel ID
prompt_input "📌 Enter Live Status Channel ID (Optional, press Enter to skip): " MONITOR_CHAN_ID ""

# 3. Ask for Alert Channel ID
prompt_input "🚨 Enter Alert Channel ID (Optional, press Enter to skip): " ALERT_CHAN_ID ""

# 4. Ask for Web Dashboard Port
prompt_input "🌐 Enter Web Dashboard Port [Default: 8080]: " INPUT_PORT "8080"
WEB_PORT=${INPUT_PORT:-8080}

REFRESH_INTERVAL=2

echo -e "\n${CYAN}---------------------------------------------------------------------${NC}"
echo -e "${GREEN}✅ Installation Summary:${NC}"
echo -e " • Bot Token:              ${CYAN}${BOT_TOKEN:0:18}...${NC}"
echo -e " • Live Status Channel ID: ${CYAN}${MONITOR_CHAN_ID:-None}${NC}"
echo -e " • Alert Channel ID:       ${CYAN}${ALERT_CHAN_ID:-None}${NC}"
echo -e " • Web Dashboard Port:     ${CYAN}${WEB_PORT}${NC}"
echo -e " • Refresh Interval:       ${CYAN}2 seconds (Real-Time)${NC}"
echo -e "${CYAN}---------------------------------------------------------------------${NC}\n"

prompt_input "Proceed with installation on this server? (y/n) [Default: y]: " CONFIRM "y"
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo -e "${RED}Installation cancelled by user.${NC}"
  exit 0
fi

# Step 1: Install Dependencies
echo -e "\n${YELLOW}📦 [1/5] Installing OS dependencies (Python3, venv, git, curl)...${NC}"
if command -v apt-get &>/dev/null; then
  apt-get update -y
  apt-get install -y python3 python3-pip python3-venv git curl
elif command -v yum &>/dev/null; then
  yum install -y python3 python3-pip git curl
elif command -v dnf &>/dev/null; then
  dnf install -y python3 python3-pip git curl
fi

# Step 2: Prepare Application Directory
INSTALL_DIR="/opt/vps-monitor-bot"
echo -e "${YELLOW}📂 [2/5] Setting up project directory at ${INSTALL_DIR}...${NC}"
mkdir -p "$INSTALL_DIR"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" 2>/dev/null && pwd || echo "" )"

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/bot.py" ]; then
  cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR"/ 2>/dev/null || true
fi

cd "$INSTALL_DIR"

# If files don't exist in /opt/vps-monitor-bot (e.g. executed via curl single liner), clone repo or write core files
if [ ! -f "$INSTALL_DIR/bot.py" ]; then
  echo -e "${YELLOW}📥 Fetching application source code from repository...${NC}"
  git clone https://github.com/Rudra-Sarkarr/ServerPulse.git "$INSTALL_DIR" 2>/dev/null || true
fi

# Step 3: Python Environment & Packages
echo -e "${YELLOW}🐍 [3/5] Installing Python packages...${NC}"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/venv/bin/pip" install discord.py psutil python-dotenv tabulate --quiet

# Step 4: Write Environment Config
echo -e "${YELLOW}⚙️ [4/5] Generating .env file...${NC}"
cat <<EOF > "$INSTALL_DIR/.env"
DISCORD_TOKEN=${BOT_TOKEN}
MONITOR_CHANNEL_ID=${MONITOR_CHAN_ID}
ALERT_CHANNEL_ID=${ALERT_CHAN_ID}
REFRESH_INTERVAL=${REFRESH_INTERVAL}
CPU_ALERT_THRESHOLD=85
RAM_ALERT_THRESHOLD=85
DISK_ALERT_THRESHOLD=90
ALERT_COOLDOWN=300
WEB_HOST=0.0.0.0
WEB_PORT=${WEB_PORT}
EOF

chmod 600 "$INSTALL_DIR/.env"

# Step 5: Setup Systemd 24/7 Service
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
echo -e "🌐 ${BOLD}Web Dashboard:${NC}    ${CYAN}http://${VPS_IP}:${WEB_PORT}${NC}"
echo -e "📂 ${BOLD}Directory:${NC}        ${INSTALL_DIR}"
echo -e ""
echo -e "${YELLOW}Useful Service Commands:${NC}"
echo -e " • Check Status: ${CYAN}systemctl status vps-monitor-bot${NC}"
echo -e " • View Logs:     ${CYAN}journalctl -u vps-monitor-bot -f${NC}"
echo -e " • Restart:       ${CYAN}systemctl restart vps-monitor-bot${NC}"
echo -e " • Edit Config:   ${CYAN}nano ${INSTALL_DIR}/.env${NC}"
echo "====================================================================="
