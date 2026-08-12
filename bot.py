import asyncio
import logging
import sys
import discord
from discord.ext import commands
from config import Config

# Configure clean logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("vps_monitor")

class VPSMonitorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        """Load extensions and sync application slash commands."""
        cogs = ["cogs.status", "cogs.live_dashboard", "cogs.alerts"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Successfully loaded extension: {cog}")
            except Exception as e:
                logger.error(f"Failed to load extension {cog}: {e}")

        # Sync slash commands
        if Config.GUILD_ID:
            guild = discord.Object(id=Config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} slash commands instantly to Guild ID {Config.GUILD_ID}")
        else:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands globally")

    async def on_ready(self):
        logger.info(f"🚀 Bot connected as {self.user} (ID: {self.user.id})")
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="VPS RAM, CPU & Disk | /stats"
        )
        await self.change_presence(activity=activity)
        
        # Start Web Dashboard HTTP Server
        from web_server import WebDashboardServer
        web_server = WebDashboardServer()
        web_server.start(bot=self)

async def main():
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        logger.info("Please create and populate your .env file using .env.example as template.")
        sys.exit(1)

    bot = VPSMonitorBot()
    async with bot:
        await bot.start(Config.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot execution stopped by user.")
