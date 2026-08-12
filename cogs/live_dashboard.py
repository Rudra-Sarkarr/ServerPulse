import logging
import discord
from discord.ext import commands, tasks
from utils.embeds import create_system_overview_embed
from cogs.status import DashboardView
from config import Config

logger = logging.getLogger("vps_monitor.live_dashboard")

class LiveDashboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dashboard_message: discord.Message = None
        if Config.MONITOR_CHANNEL_ID:
            self.live_dashboard_task.start()

    def cog_unload(self):
        if self.live_dashboard_task.is_running():
            self.live_dashboard_task.cancel()

    @tasks.loop(seconds=max(2, Config.REFRESH_INTERVAL))
    async def live_dashboard_task(self):
        """Periodically update the persistent status message in the configured channel."""
        if not Config.MONITOR_CHANNEL_ID:
            return

        channel = self.bot.get_channel(Config.MONITOR_CHANNEL_ID)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(Config.MONITOR_CHANNEL_ID)
            except Exception as e:
                logger.warning(f"Could not find monitor channel with ID {Config.MONITOR_CHANNEL_ID}: {e}")
                return

        embed = create_system_overview_embed()
        view = DashboardView(current_type="overview")

        # Try updating existing dashboard message
        if self.dashboard_message:
            try:
                await self.dashboard_message.edit(embed=embed, view=view)
                return
            except discord.NotFound:
                self.dashboard_message = None
            except Exception as e:
                logger.error(f"Error editing live dashboard message: {e}")
                self.dashboard_message = None

        # Look for existing message sent by bot in the channel history
        if not self.dashboard_message:
            try:
                async for message in channel.history(limit=20):
                    if message.author.id == self.bot.user.id and message.embeds and "VPS Real-Time Resource Dashboard" in (message.embeds[0].title or ""):
                        self.dashboard_message = message
                        await self.dashboard_message.edit(embed=embed, view=view)
                        return
            except Exception as e:
                logger.debug(f"History search error: {e}")

        # Send new dashboard message if none found
        try:
            self.dashboard_message = await channel.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Failed to send initial live dashboard message: {e}")

    @live_dashboard_task.before_loop
    async def before_live_dashboard(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LiveDashboardCog(bot))
