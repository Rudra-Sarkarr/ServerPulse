import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from utils.metrics import (
    get_complete_system_summary,
    get_top_processes,
    get_cpu_metrics,
    get_ram_metrics,
    get_disk_metrics,
    get_network_metrics,
    get_system_info
)
from config import Config

logger = logging.getLogger("vps_monitor.web_server")

# Reference to Discord Bot instance (set when server starts)
bot_instance = None

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard")

class DashboardRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Silence default HTTP request logging to keep console clean."""
        pass

    def send_json(self, data: dict, status_code: int = 200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, filepath: str, content_type: str):
        if not os.path.exists(filepath):
            self.send_error(404, "File Not Found")
            return
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Server Error: {e}")

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Static assets routing
        if path in ("/", "/index.html"):
            self.serve_file(os.path.join(DASHBOARD_DIR, "index.html"), "text/html; charset=utf-8")
            return
        elif path == "/style.css":
            self.serve_file(os.path.join(DASHBOARD_DIR, "style.css"), "text/css; charset=utf-8")
            return
        elif path == "/app.js":
            self.serve_file(os.path.join(DASHBOARD_DIR, "app.js"), "application/javascript; charset=utf-8")
            return
        elif path == "/logo.jpg":
            self.serve_file(os.path.join(DASHBOARD_DIR, "logo.jpg"), "image/jpeg")
            return

        # API Endpoints
        if path == "/api/metrics":
            try:
                metrics = get_complete_system_summary()
                self.send_json(metrics)
            except Exception as e:
                self.send_json({"error": str(e)}, status_code=500)
            return

        elif path == "/api/processes":
            query_params = parse_qs(parsed_url.query)
            sort_by = query_params.get("sort_by", ["cpu"])[0]
            limit = int(query_params.get("limit", [30])[0])
            try:
                procs = get_top_processes(limit=limit, sort_by=sort_by)
                self.send_json({"processes": procs, "count": len(procs)})
            except Exception as e:
                self.send_json({"error": str(e)}, status_code=500)
            return

        elif path == "/api/bot/status":
            is_online = bot_instance is not None and bot_instance.is_ready()
            bot_info = {
                "online": is_online,
                "name": str(bot_instance.user) if is_online else "Offline",
                "ping_ms": round(bot_instance.latency * 1000, 1) if is_online and hasattr(bot_instance, 'latency') else None,
                "guilds_count": len(bot_instance.guilds) if is_online else 0,
                "monitor_channel_configured": bool(Config.MONITOR_CHANNEL_ID),
                "alert_channel_configured": bool(Config.ALERT_CHANNEL_ID),
                "refresh_interval": Config.REFRESH_INTERVAL,
                "cpu_threshold": Config.CPU_ALERT_THRESHOLD,
                "ram_threshold": Config.RAM_ALERT_THRESHOLD,
                "disk_threshold": Config.DISK_ALERT_THRESHOLD
            }
            self.send_json(bot_info)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == "/api/bot/test-alert":
            if not bot_instance or not bot_instance.is_ready():
                self.send_json({"success": False, "message": "Discord bot is offline"}, status_code=400)
                return

            if not Config.ALERT_CHANNEL_ID:
                self.send_json({"success": False, "message": "ALERT_CHANNEL_ID is not configured in .env"}, status_code=400)
                return

            channel = bot_instance.get_channel(Config.ALERT_CHANNEL_ID)
            if channel:
                from utils.embeds import create_alert_embed
                import asyncio
                embed = create_alert_embed("TEST ALERT", 95.0, Config.CPU_ALERT_THRESHOLD)
                asyncio.run_coroutine_threadsafe(channel.send(content="🧪 **MANUAL TEST ALERT FROM WEB DASHBOARD**", embed=embed), bot_instance.loop)
                self.send_json({"success": True, "message": f"Test alert dispatched to channel {Config.ALERT_CHANNEL_ID}"})
            else:
                self.send_json({"success": False, "message": f"Could not find channel {Config.ALERT_CHANNEL_ID}"}, status_code=404)
            return

        self.send_error(404, "Not Found")


class WebDashboardServer:
    def __init__(self, host: str = Config.WEB_HOST, port: int = Config.WEB_PORT):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self, bot=None):
        global bot_instance
        bot_instance = bot
        try:
            self.server = HTTPServer((self.host, self.port), DashboardRequestHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"🌐 Web Dashboard server running at http://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start Web Dashboard server on port {self.port}: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Web Dashboard server stopped.")
