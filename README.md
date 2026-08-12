# 🖥️ Discord VPS Real-Time Resource Monitoring Bot

A high-performance Discord Bot built in Python (`discord.py` & `psutil`) that monitors your VPS server's **RAM, CPU, Disk, Network, and Process usage** in real-time. Features auto-updating channel dashboards, interactive buttons/dropdowns, slash commands, and high-resource alert notifications.

---

## 🔥 Features

- ⚡ **Real-Time CPU Usage**: Total CPU %, per-core breakdown, clock frequency, and system load averages (1m, 5m, 15m).
- 🧠 **Memory Monitoring**: RAM total/used/free/available, cached/buffers, and Swap memory breakdown.
- 💾 **Disk & Storage**: Root partition status, list of all mounted partitions, free space, and read/write I/O stats.
- 🌐 **Network Traffic**: Live upload and download speeds, total data transferred, and packet counts.
- 🔥 **Top Process List**: View top 10 CPU or RAM consuming processes directly inside Discord.
- 🔄 **Live Channel Dashboard**: Auto-updates a single persistent message in a dedicated Discord channel every X seconds.
- 🎛️ **Interactive UI**: Buttons to refresh stats instantly and dropdown select menus to switch views on demand.
- 🚨 **Threshold Alert System**: Automated background monitor that alerts your admin channel when CPU, RAM, or Disk cross high-usage limits.
- 🚀 **VPS Ready**: Includes Linux `systemd` service script and Docker configuration for 24/7 background operation.

## ⚡ 1-Click Interactive Ubuntu VPS Installer

Run this single command on your Ubuntu VPS. The terminal will interactively ask for your **Discord Bot Token**, **Channel IDs**, and **Port**, then automatically install all dependencies and set up the 24/7 background service!

```bash
sudo bash install.sh
```

---

## 🛠️ Step 1: Create Your Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, give it a name (e.g. `VPS Monitor`), and create it.
3. Navigate to the **Bot** tab on the left menu:
   - Click **Reset Token** (or **Add Bot**) and copy your **Bot Token**. *(Keep this secret!)*
4. Navigate to **OAuth2 -> URL Generator**:
   - Under **Scopes**, check: `bot` and `applications.commands`.
   - Under **Bot Permissions**, check:
     - `Send Messages`
     - `Embed Links`
     - `Read Message History`
     - `Use Slash Commands`
   - Copy the generated URL at the bottom and open it in your browser to invite the bot to your Discord server.

---

## 🚀 Step 2: Installation & Configuration

### 1. Clone or Copy Files to your VPS
```bash
cd /opt
git clone <your-repo-url> vps-monitor-bot
cd vps-monitor-bot
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Setup `.env` Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
nano .env
```

Fill in your configuration:
```env
DISCORD_TOKEN=your_discord_bot_token_here
GUILD_ID=123456789012345678          # Optional: Guild ID for instant slash command sync
MONITOR_CHANNEL_ID=123456789012345678# Channel ID where auto-updating status stays pinned
ALERT_CHANNEL_ID=123456789012345678  # Channel ID for high resource alert notifications
REFRESH_INTERVAL=10                  # Dashboard edit interval in seconds (>= 5s)
CPU_ALERT_THRESHOLD=85               # Warn when CPU > 85%
RAM_ALERT_THRESHOLD=85               # Warn when RAM > 85%
DISK_ALERT_THRESHOLD=90              # Warn when Disk > 90%
```

---

## 🎮 Slash Command Reference

| Command | Description |
| :--- | :--- |
| `/stats` | Full interactive server overview dashboard with refresh buttons |
| `/cpu` | Detailed CPU breakdown per core, clock speed & load averages |
| `/ram` | Physical RAM allocation, available memory, and Swap stats |
| `/disk` | Mounted partitions, root partition free space & disk I/O |
| `/network` | Live upload/download bandwidth speed & total traffic |
| `/top` | Top 10 CPU or RAM hog processes running on the VPS |
| `/vpshelp` | Help menu listing commands and usage info |

---

## 📦 Step 3: Run 24/7 on VPS

### Option A: Using `systemd` (Recommended for Linux VPS)

1. Copy the systemd service file:
```bash
cp vps-monitor-bot.service /etc/systemd/system/vps-monitor-bot.service
```

2. Reload daemon and start service:
```bash
systemctl daemon-reload
systemctl enable vps-monitor-bot
systemctl start vps-monitor-bot
```

3. Check service status & logs:
```bash
systemctl status vps-monitor-bot
journalctl -u vps-monitor-bot -f
```

---

### Option B: Using Docker & Docker Compose

```bash
docker-compose up -d --build
```

View logs:
```bash
docker-compose logs -f
```

---

## 📂 Project Structure

```
├── bot.py                  # Main entry point & client setup
├── config.py               # Environment configuration parser
├── cogs/
│   ├── status.py           # Slash commands & interactive UI views
│   ├── live_dashboard.py   # Continuous auto-updating channel task
│   └── alerts.py           # Automated resource alert monitor
├── utils/
│   ├── metrics.py          # System hardware & OS psutil metrics engine
│   └── embeds.py           # Progress bar & Discord embed generators
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
├── vps-monitor-bot.service # Systemd background service script
├── Dockerfile              # Docker build container
└── docker-compose.yml      # Docker compose configuration
```
