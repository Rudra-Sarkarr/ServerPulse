import time
import logging
import discord
from discord.ext import commands, tasks
from utils.metrics import get_cpu_metrics, get_ram_metrics, get_disk_metrics
from utils.embeds import create_alert_embed
from config import Config

logger = logging.getLogger("vps_monitor.alerts")

class ResourceAlertsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_alerts = {
            "CPU": 0,
            "RAM": 0,
            "Disk": 0
        }
        if Config.ALERT_CHANNEL_ID:
            self.alert_check_task.start()

    def cog_unload(self):
        if self.alert_check_task.is_running():
            self.alert_check_task.cancel()

    @tasks.loop(seconds=15)
    async def alert_check_task(self):
        """Check server resources against configured warning thresholds."""
        if not Config.ALERT_CHANNEL_ID:
            return

        channel = self.bot.get_channel(Config.ALERT_CHANNEL_ID)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(Config.ALERT_CHANNEL_ID)
            except Exception as e:
                logger.warning(f"Alert channel ID {Config.ALERT_CHANNEL_ID} not accessible: {e}")
                return

        now = time.time()
        cpu = get_cpu_metrics()
        ram = get_ram_metrics()
        disk = get_disk_metrics()

        alerts_to_send = []

        # Check CPU
        if cpu["total_percent"] >= Config.CPU_ALERT_THRESHOLD:
            if now - self.last_alerts["CPU"] > Config.ALERT_COOLDOWN:
                alerts_to_send.append(("CPU", cpu["total_percent"], Config.CPU_ALERT_THRESHOLD))
                self.last_alerts["CPU"] = now

        # Check RAM
        if ram["percent"] >= Config.RAM_ALERT_THRESHOLD:
            if now - self.last_alerts["RAM"] > Config.ALERT_COOLDOWN:
                alerts_to_send.append(("RAM", ram["percent"], Config.RAM_ALERT_THRESHOLD))
                self.last_alerts["RAM"] = now

        # Check Disk
        if disk["root_percent"] >= Config.DISK_ALERT_THRESHOLD:
            if now - self.last_alerts["Disk"] > Config.ALERT_COOLDOWN:
                alerts_to_send.append(("Disk Storage", disk["root_percent"], Config.DISK_ALERT_THRESHOLD))
                self.last_alerts["Disk"] = now

        # Dispatch alert embeds
        for resource_name, current_val, threshold_val in alerts_to_send:
            try:
                embed = create_alert_embed(resource_name, current_val, threshold_val)
                await channel.send(content="🚨 **ATTENTION ADMINS**", embed=embed)
                logger.info(f"Dispatched {resource_name} alert ({current_val}%) to channel {Config.ALERT_CHANNEL_ID}")
            except Exception as e:
                logger.error(f"Failed to send alert for {resource_name}: {e}")

    @alert_check_task.before_loop
    async def before_alert_check(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(ResourceAlertsCog(bot))
