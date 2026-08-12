import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import (
    create_btop_dashboard_embed,
    create_cpu_embed,
    create_ram_embed,
    create_disk_embed,
    create_network_embed,
    create_top_processes_embed
)
from config import Config

logger = logging.getLogger("vps_monitor.status")

def get_embed_for_type(view_type: str) -> discord.Embed:
    if view_type == "cpu":
        return create_cpu_embed()
    elif view_type == "ram":
        return create_ram_embed()
    elif view_type == "disk":
        return create_disk_embed()
    elif view_type == "network":
        return create_network_embed()
    elif view_type == "top_cpu":
        return create_top_processes_embed(sort_by="cpu")
    elif view_type == "top_ram":
        return create_top_processes_embed(sort_by="ram")
    else:
        return create_btop_dashboard_embed()


class DashboardSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="btop Dashboard Overview", value="overview", description="Main CPU, RAM, Disk & Network dashboard", emoji="🖥️"),
            discord.SelectOption(label="CPU Breakdown", value="cpu", description="Per-core usage, frequency & load averages", emoji="⚡"),
            discord.SelectOption(label="Memory (RAM & Swap)", value="ram", description="RAM allocation, free/cached & Swap memory", emoji="🧠"),
            discord.SelectOption(label="Disk & Storage", value="disk", description="Mounted partitions, free space & disk I/O", emoji="💾"),
            discord.SelectOption(label="Network Bandwidth", value="network", description="Upload/download speeds & traffic stats", emoji="🌐"),
            discord.SelectOption(label="Top Processes (CPU)", value="top_cpu", description="Top 10 CPU consuming processes", emoji="🔥"),
            discord.SelectOption(label="Top Processes (RAM)", value="top_ram", description="Top 10 RAM consuming processes", emoji="📊"),
        ]
        super().__init__(placeholder="🔍 Select detailed metric view...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view_type = self.values[0]
        if hasattr(self.view, 'current_type'):
            self.view.current_type = view_type
        embed = get_embed_for_type(view_type)
        await interaction.response.edit_message(embed=embed, view=self.view)


class DashboardView(discord.ui.View):
    def __init__(self, current_type: str = "overview"):
        super().__init__(timeout=600) # 10 minutes active timeout
        self.current_type = current_type
        self.add_item(DashboardSelect())

    @discord.ui.button(label="Refresh Stats", style=discord.ButtonStyle.primary, emoji="🔄", row=1)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        select_item = self.children[0]
        selected_type = select_item.values[0] if hasattr(select_item, 'values') and select_item.values else self.current_type
        embed = get_embed_for_type(selected_type)
        await interaction.response.edit_message(embed=embed, view=self)


class StatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_update_tasks: dict[int, asyncio.Task] = {}

    def cog_unload(self):
        for task in self.active_update_tasks.values():
            task.cancel()

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if not Config.ALLOWED_ROLES:
            return True
        user_roles = [r.id for r in getattr(interaction.user, 'roles', [])]
        return any(rid in Config.ALLOWED_ROLES for rid in user_roles) or interaction.user.id in Config.ALLOWED_ROLES

    async def _register_live_update(self, interaction: discord.Interaction, view: DashboardView):
        """Register a background task to auto-refresh the message embed every 2 seconds."""
        try:
            msg = await interaction.original_response()
            msg_id = msg.id

            if msg_id in self.active_update_tasks:
                self.active_update_tasks[msg_id].cancel()

            async def live_loop():
                while True:
                    await asyncio.sleep(max(2, Config.REFRESH_INTERVAL))
                    try:
                        embed = get_embed_for_type(view.current_type)
                        await msg.edit(embed=embed, view=view)
                    except (discord.NotFound, discord.HTTPException):
                        break
                    except Exception as e:
                        logger.debug(f"Live loop exception: {e}")

            task = asyncio.create_task(live_loop())
            self.active_update_tasks[msg_id] = task
        except Exception as e:
            logger.error(f"Failed to register live update for response message: {e}")

    @app_commands.command(name="stats", description="Show full real-time VPS server status dashboard (Auto-refreshes every 2s)")
    async def stats(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            await interaction.response.send_message("❌ You are not authorized to run this command.", ephemeral=True)
            return

        embed = create_btop_dashboard_embed()
        view = DashboardView(current_type="overview")
        await interaction.response.send_message(embed=embed, view=view)
        await self._register_live_update(interaction, view)

    @app_commands.command(name="cpu", description="Show detailed CPU usage per core & load averages (Auto-refreshes every 2s)")
    async def cpu(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            await interaction.response.send_message("❌ You are not authorized to run this command.", ephemeral=True)
            return

        embed = create_cpu_embed()
        view = DashboardView(current_type="cpu")
        await interaction.response.send_message(embed=embed, view=view)
        await self._register_live_update(interaction, view)

    @app_commands.command(name="ram", description="Show detailed RAM memory and Swap usage (Auto-refreshes every 2s)")
    async def ram(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            await interaction.response.send_message("❌ You are not authorized to run this command.", ephemeral=True)
            return

        embed = create_ram_embed()
        view = DashboardView(current_type="ram")
        await interaction.response.send_message(embed=embed, view=view)
        await self._register_live_update(interaction, view)

    @app_commands.command(name="disk", description="Show disk partition storage and I/O stats (Auto-refreshes every 2s)")
    async def disk(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            await interaction.response.send_message("❌ You are not authorized to run this command.", ephemeral=True)
            return

        embed = create_disk_embed()
        view = DashboardView(current_type="disk")
        await interaction.response.send_message(embed=embed, view=view)
        await self._register_live_update(interaction, view)

    @app_commands.command(name="network", description="Show network download/upload bandwidth speeds (Auto-refreshes every 2s)")
    async def network(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            await interaction.response.send_message("❌ You are not authorized to run this command.", ephemeral=True)
            return

        embed = create_network_embed()
        view = DashboardView(current_type="network")
        await interaction.response.send_message(embed=embed, view=view)
        await self._register_live_update(interaction, view)

    @app_commands.command(name="top", description="Show top 10 CPU or RAM consuming processes on the VPS (Auto-refreshes every 2s)")
    @app_commands.choices(sort_by=[
        app_commands.Choice(name="CPU Usage", value="cpu"),
        app_commands.Choice(name="RAM Usage", value="ram")
    ])
    async def top(self, interaction: discord.Interaction, sort_by: app_commands.Choice[str] = None):
        if not self.is_authorized(interaction):
            await interaction.response.send_message("❌ You are not authorized to run this command.", ephemeral=True)
            return

        metric = sort_by.value if sort_by else "cpu"
        embed = create_top_processes_embed(sort_by=metric)
        view = DashboardView(current_type=f"top_{metric}")
        await interaction.response.send_message(embed=embed, view=view)
        await self._register_live_update(interaction, view)

    @app_commands.command(name="vpshelp", description="Display available VPS monitor bot commands and features")
    async def vpshelp(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 VPS Monitor Bot - Help & Command List",
            description="Real-time monitoring bot for CPU, RAM, Disk, and Network usage on your server.",
            color=0x00F0FF
        )
        embed.add_field(name="/stats", value="Full btop dashboard overview (Auto-refreshes every 2s).", inline=False)
        embed.add_field(name="/cpu", value="Per-core CPU usage, clock frequency & load averages.", inline=False)
        embed.add_field(name="/ram", value="RAM allocation, buffer/cached & Swap memory.", inline=False)
        embed.add_field(name="/disk", value="Mounted disk partitions, free space & disk I/O.", inline=False)
        embed.add_field(name="/network", value="Real-time upload/download bandwidth speeds.", inline=False)
        embed.add_field(name="/top [sort_by]", value="List top 10 CPU or RAM consuming processes.", inline=False)
        embed.set_footer(text="Tip: Embeds auto-refresh live every 2 seconds!")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
