import logging
import discord
from discord.ext import commands, tasks
from utils.embeds import create_btop_dashboard_embed
from cogs.status import DashboardView
from config import Config

logger = logging.getLogger("vps_monitor.live_dashboard")

class LiveDashboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dashboard_message: discord.Message = None
        self.live_dashboard_task.start()

    def cog_unload(self):
        if self.live_dashboard_task.is_running():
            self.live_dashboard_task.cancel()

    async def _get_or_create_status_channel(self) -> discord.TextChannel:
        """Fetch configured channel ID or auto-detect/create #server-status channel in Guild."""
        if Config.MONITOR_CHANNEL_ID:
            channel = self.bot.get_channel(Config.MONITOR_CHANNEL_ID)
            if channel:
                return channel
            try:
                return await self.bot.fetch_channel(Config.MONITOR_CHANNEL_ID)
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
                # Search for existing #server-status channel
                for ch in getattr(guild, 'text_channels', []):
                    if ch.name in ("server-status", "vps-status", "status-dashboard"):
                        return ch

                # Auto-create #server-status channel if bot has permissions
                try:
                    ch = await guild.create_text_channel("server-status", topic="⚡ Real-time VPS Server Status Dashboard")
                    logger.info(f"Auto-created #server-status channel in Guild {guild.name} ({guild.id})")
                    return ch
                except Exception as e:
                    logger.warning(f"Could not auto-create #server-status channel in Guild: {e}")

        return None

    @tasks.loop(seconds=max(2, Config.REFRESH_INTERVAL))
    async def live_dashboard_task(self):
        """Periodically update persistent live dashboard embed in the server channel."""
        channel = await self._get_or_create_status_channel()
        if not channel:
            return

        embed = create_btop_dashboard_embed()
        view = DashboardView(current_type="overview")

        # Try editing existing dashboard message
        if self.dashboard_message:
            try:
                await self.dashboard_message.edit(embed=embed, view=view)
                return
            except discord.NotFound:
                self.dashboard_message = None
            except Exception as e:
                logger.error(f"Error editing live dashboard message: {e}")
                self.dashboard_message = None

        # Look for existing dashboard message in channel history
        if not self.dashboard_message:
            try:
                async for message in channel.history(limit=20):
                    if message.author.id == self.bot.user.id and message.embeds and ("VPS REAL-TIME" in (message.embeds[0].title or "") or "VPS Real-Time" in (message.embeds[0].title or "")):
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
