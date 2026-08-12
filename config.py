import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

class Config:
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    
    _guild_id_str = os.getenv("GUILD_ID", "").strip()
    GUILD_ID: int = int(_guild_id_str) if _guild_id_str.isdigit() else None

    _monitor_chan_str = os.getenv("MONITOR_CHANNEL_ID", "").strip()
    MONITOR_CHANNEL_ID: int = int(_monitor_chan_str) if _monitor_chan_str.isdigit() else None

    _alert_chan_str = os.getenv("ALERT_CHANNEL_ID", "").strip()
    ALERT_CHANNEL_ID: int = int(_alert_chan_str) if _alert_chan_str.isdigit() else None

    REFRESH_INTERVAL: int = int(os.getenv("REFRESH_INTERVAL", 2))
    
    # Alert Thresholds
    CPU_ALERT_THRESHOLD: float = float(os.getenv("CPU_ALERT_THRESHOLD", 85.0))
    RAM_ALERT_THRESHOLD: float = float(os.getenv("RAM_ALERT_THRESHOLD", 85.0))
    DISK_ALERT_THRESHOLD: float = float(os.getenv("DISK_ALERT_THRESHOLD", 90.0))
    ALERT_COOLDOWN: int = int(os.getenv("ALERT_COOLDOWN", 300))

    # Web Settings
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("WEB_PORT", 8080))
    DOMAIN_NAME: str = os.getenv("DOMAIN_NAME", "").strip()
    USE_DOMAIN: bool = os.getenv("USE_DOMAIN", "false").lower() in ("true", "1", "yes")

    # Allowed Roles / Users
    _allowed_roles_str = os.getenv("ALLOWED_ROLES", "").strip()
    ALLOWED_ROLES: list[int] = [
        int(r.strip()) for r in _allowed_roles_str.split(",") if r.strip().isdigit()
    ] if _allowed_roles_str else []

    @classmethod
    def validate(cls):
        if not cls.DISCORD_TOKEN or cls.DISCORD_TOKEN == "your_discord_bot_token_here":
            raise ValueError("DISCORD_TOKEN is missing! Please configure DISCORD_TOKEN in .env")
