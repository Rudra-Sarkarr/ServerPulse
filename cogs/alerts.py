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
        self.alert_check_task.start()

    def cog_unload(self):
        if self.alert_check_task.is_running():
            self.alert_check_task.cancel()

    async def _get_or_create_alerts_channel(self) -> discord.TextChannel:
        """Fetch configured alert channel ID or auto-detect/create #server-alerts in Guild."""
        if Config.ALERT_CHANNEL_ID:
            channel = self.bot.get_channel(Config.ALERT_CHANNEL_ID)
            if channel:
                return channel
            try:
                return await self.bot.fetch_channel(Config.ALERT_CHANNEL_ID)
            except Exception:
                pass

        if Config.GUILD_ID:
            guild = self.bot.get_guild(Config.GUILD_ID)
            if not guild:
                try:
                    guild = await self.bot.fetch_guild(Config.GUILD_ID)
                except Exception:
                    pass

            if guild:
                for ch in getattr(guild, 'text_channels', []):
                    if ch.name in ("server-alerts", "vps-alerts", "alerts"):
                        return ch

                try:
                    ch = await guild.create_text_channel("server-alerts", topic="🚨 VPS High Resource Alerts")
                    logger.info(f"Auto-created #server-alerts channel in Guild {guild.name} ({guild.id})")
                    return ch
                except Exception as e:
                    logger.warning(f"Could not auto-create #server-alerts channel: {e}")

        return None

    @tasks.loop(seconds=15)
    async def alert_check_task(self):
        """Check server resources against configured warning thresholds."""
        channel = await self._get_or_create_alerts_channel()
        if not channel:
            return

        now = time.time()
        cpu = get_cpu_metrics()
        ram = get_ram_metrics()
        disk = get_disk_metrics()

        alerts_to_send = []

        if cpu["total_percent"] >= Config.CPU_ALERT_THRESHOLD:
            if now - self.last_alerts["CPU"] > Config.ALERT_COOLDOWN:
                alerts_to_send.append(("CPU", cpu["total_percent"], Config.CPU_ALERT_THRESHOLD))
                self.last_alerts["CPU"] = now

        if ram["percent"] >= Config.RAM_ALERT_THRESHOLD:
            if now - self.last_alerts["RAM"] > Config.ALERT_COOLDOWN:
                alerts_to_send.append(("RAM", ram["percent"], Config.RAM_ALERT_THRESHOLD))
                self.last_alerts["RAM"] = now

        if disk["root_percent"] >= Config.DISK_ALERT_THRESHOLD:
            if now - self.last_alerts["Disk"] > Config.ALERT_COOLDOWN:
                alerts_to_send.append(("Disk Storage", disk["root_percent"], Config.DISK_ALERT_THRESHOLD))
                self.last_alerts["Disk"] = now

        for resource_name, current_val, threshold_val in alerts_to_send:
            try:
                embed = create_alert_embed(resource_name, current_val, threshold_val)
                await channel.send(content="🚨 **ATTENTION ADMINS**", embed=embed)
                logger.info(f"Dispatched {resource_name} alert ({current_val}%) to channel {channel.name} ({channel.id})")
            except Exception as e:
                logger.error(f"Failed to send alert for {resource_name}: {e}")

    @alert_check_task.before_loop
    async def before_alert_check(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(ResourceAlertsCog(bot))
