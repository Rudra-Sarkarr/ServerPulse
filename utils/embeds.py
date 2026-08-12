import discord
from datetime import datetime
from tabulate import tabulate
from utils.metrics import (
    make_progress_bar,
    get_cpu_metrics,
    get_ram_metrics,
    get_disk_metrics,
    get_network_metrics,
    get_system_info,
    get_top_processes,
    get_complete_system_summary
)

COLOR_HEALTHY = 0x2ECC71  # Emerald Green
COLOR_WARNING = 0xF1C40F  # Yellow
COLOR_DANGER  = 0xE74C3C  # Red
COLOR_INFO    = 0x00F0FF  # Cyber Cyan

def get_status_color(max_percent: float) -> int:
    if max_percent >= 85.0:
        return COLOR_DANGER
    elif max_percent >= 70.0:
        return COLOR_WARNING
    return COLOR_HEALTHY

def make_ascii_bar(percent: float, length: int = 20, fill_char: str = "█", empty_char: str = "░") -> str:
    """Generate a clean ASCII bar for codeblocks."""
    percent = max(0.0, min(100.0, percent))
    filled = int(round(length * percent / 100))
    return fill_char * filled + empty_char * (length - filled)

def create_btop_dashboard_embed(summary: dict = None) -> discord.Embed:
    """Build a terminal btop/htop styled Discord Embed Dashboard."""
    if summary is None:
        summary = get_complete_system_summary()

    sys_info = summary["system"]
    cpu = summary["cpu"]
    ram = summary["ram"]
    disk = summary["disk"]
    net = summary["network"]

    max_pct = max(cpu["total_percent"], ram["percent"], disk["root_percent"])
    embed_color = get_status_color(max_pct)

    embed = discord.Embed(
        title="🖥️ VPS REAL-TIME MONITORING DASHBOARD",
        description=f"**Host:** `{sys_info['hostname']}` | **OS:** `{sys_info['os']}` | **Uptime:** `{sys_info['uptime']}`",
        color=embed_color,
        timestamp=datetime.now()
    )

    # 1. CPU Section Codeblock
    cpu_bar = make_ascii_bar(cpu["total_percent"], length=22)
    per_core_lines = []
    per_core_pcts = cpu["per_core_percent"]
    
    # Format cores 2-per-line
    for i in range(0, len(per_core_pcts), 2):
        c1 = f"C{i:02d}: {per_core_pcts[i]:4.1f}%"
        if i + 1 < len(per_core_pcts):
            c2 = f"C{i+1:02d}: {per_core_pcts[i+1]:4.1f}%"
            per_core_lines.append(f"{c1}  │  {c2}")
        else:
            per_core_lines.append(c1)
    
    # Limit displayed core lines if high core count (e.g. max 4 lines)
    if len(per_core_lines) > 4:
        per_core_str = "\n".join(per_core_lines[:4]) + f"\n... +{len(per_core_lines)-4} more cores"
    else:
        per_core_str = "\n".join(per_core_lines) if per_core_lines else "N/A"

    cpu_block = (
        "```yaml\n"
        f"┌─ CPU USAGE [{cpu['total_percent']:5.1f}%] ──────────────────────────┐\n"
        f"│ [{cpu_bar}] │\n"
        f"├─ CORES ({cpu['physical_cores']} Physical / {cpu['logical_cores']} Logical) ──────────────┤\n"
        f"{per_core_str}\n"
        f"├─ LOAD AVERAGE ──────────────────────────────────┤\n"
        f"│ 1m: {cpu['load_1']:<5} │ 5m: {cpu['load_5']:<5} │ 15m: {cpu['load_15']:<5}          │\n"
        "└─────────────────────────────────────────────────┘\n"
        "```"
    )
    embed.add_field(name="⚡ CPU MONITOR", value=cpu_block, inline=False)

    # 2. Memory & Storage Section Codeblock
    ram_bar = make_ascii_bar(ram["percent"], length=22)
    swap_bar = make_ascii_bar(ram["swap_percent"], length=22)
    disk_bar = make_ascii_bar(disk["root_percent"], length=22)

    mem_disk_block = (
        "```yaml\n"
        f"┌─ MEMORY (RAM) [{ram['percent']:5.1f}%] ───────────────────────┐\n"
        f"│ [{ram_bar}] │\n"
        f"│ Used: {ram['used_str']} / {ram['total_str']} | Free: {ram['free_str']} │\n"
        f"├─ SWAP MEMORY [{ram['swap_percent']:5.1f}%] ──────────────────────┤\n"
        f"│ [{swap_bar}] │\n"
        f"├─ ROOT STORAGE (/) [{disk['root_percent']:5.1f}%] ──────────────────┤\n"
        f"│ [{disk_bar}] │\n"
        f"│ Used: {disk['root_used_str']} / {disk['root_total_str']} | Free: {disk['root_free_str']} │\n"
        "└─────────────────────────────────────────────────┘\n"
        "```"
    )
    embed.add_field(name="🧠 MEMORY & STORAGE", value=mem_disk_block, inline=False)

    # 3. Network & Top Process Section
    net_block = (
        "```yaml\n"
        "┌─ NETWORK TRAFFIC ───────────────────────────────┐\n"
        f"│ ⬇️ Download: {net['download_speed_str']:<10} (Total: {net['bytes_recv_total_str']}) │\n"
        f"│ ⬆️ Upload:   {net['upload_speed_str']:<10} (Total: {net['bytes_sent_total_str']}) │\n"
        "└─────────────────────────────────────────────────┘\n"
        "```"
    )
    embed.add_field(name="🌐 NETWORK BANDWIDTH", value=net_block, inline=False)

    embed.set_footer(text="⚡ Live btop Dashboard • Auto-refreshes in real-time • VPS Monitor Bot")
    return embed

def create_cpu_embed() -> discord.Embed:
    """Detailed per-core CPU view."""
    cpu = get_cpu_metrics()
    sys_info = get_system_info()

    embed = discord.Embed(
        title="⚡ CPU DETAILED MONITOR (btop style)",
        description=f"**Host:** `{sys_info['hostname']}` | **Processor:** `{sys_info['processor']}`",
        color=get_status_color(cpu["total_percent"]),
        timestamp=datetime.now()
    )

    total_bar = make_ascii_bar(cpu["total_percent"], length=25)
    block = f"```yaml\nTOTAL CPU: [{total_bar}] {cpu['total_percent']:5.1f}%\n"
    block += f"FREQUENCY: {cpu['freq_current_mhz'] or 'N/A'} MHz | LOAD: {cpu['load_1']} (1m), {cpu['load_5']} (5m)\n\n"
    block += "┌─ PER-CORE BREAKDOWN ────────────────────────────┐\n"

    for idx, pct in enumerate(cpu["per_core_percent"]):
        core_bar = make_ascii_bar(pct, length=15)
        block += f"│ Core {idx:02d}: [{core_bar}] {pct:5.1f}% │\n"

    block += "└─────────────────────────────────────────────────┘\n```"
    embed.description = block
    embed.set_footer(text="VPS Monitor Bot")
    return embed

def create_ram_embed() -> discord.Embed:
    """Detailed Memory view."""
    ram = get_ram_metrics()

    embed = discord.Embed(
        title="🧠 MEMORY & SWAP DETAILED MONITOR",
        color=get_status_color(ram["percent"]),
        timestamp=datetime.now()
    )

    ram_bar = make_ascii_bar(ram["percent"], length=25)
    swap_bar = make_ascii_bar(ram["swap_percent"], length=25)

    block = (
        "```yaml\n"
        f"┌─ PHYSICAL RAM [{ram['percent']:5.1f}%] ───────────────────────┐\n"
        f"│ [{ram_bar}] │\n"
        f"│ Total:     {ram['total_str']:<12} Used: {ram['used_str']:<12} │\n"
        f"│ Free:      {ram['free_str']:<12} Avail: {ram['available_str']:<12} │\n"
        "├─ SWAP MEMORY ───────────────────────────────────┤\n"
        f"│ [{swap_bar}] │\n"
        f"│ Total:     {ram['swap_total_str']:<12} Used: {ram['swap_used_str']:<12} │\n"
        "└─────────────────────────────────────────────────┘\n"
        "```"
    )
    embed.description = block
    embed.set_footer(text="VPS Monitor Bot")
    return embed

def create_disk_embed() -> discord.Embed:
    """Detailed Storage view."""
    disk = get_disk_metrics()

    embed = discord.Embed(
        title="💾 DISK STORAGE & PARTITIONS",
        color=get_status_color(disk["root_percent"]),
        timestamp=datetime.now()
    )

    root_bar = make_ascii_bar(disk["root_percent"], length=25)
    block = (
        "```yaml\n"
        f"┌─ ROOT PARTITION (/) [{disk['root_percent']:5.1f}%] ─────────────────┐\n"
        f"│ [{root_bar}] │\n"
        f"│ Total: {disk['root_total_str']:<10} Used: {disk['root_used_str']:<10} Free: {disk['root_free_str']:<10}│\n"
        "├─ MOUNTED PARTITIONS ────────────────────────────┤\n"
    )

    for p in disk["partitions"]:
        p_bar = make_ascii_bar(p["percent"], length=15)
        block += f"│ {p['mountpoint']:<10} [{p_bar}] {p['percent']:5.1f}% │\n"

    block += (
        "├─ DISK I/O TOTALS ───────────────────────────────┤\n"
        f"│ Read: {disk['read_bytes_str']:<14} Written: {disk['write_bytes_str']:<14} │\n"
        "└─────────────────────────────────────────────────┘\n"
        "```"
    )
    embed.description = block
    embed.set_footer(text="VPS Monitor Bot")
    return embed

def create_network_embed() -> discord.Embed:
    """Detailed Network view."""
    net = get_network_metrics()

    embed = discord.Embed(
        title="🌐 NETWORK TRAFFIC MONITOR",
        color=COLOR_INFO,
        timestamp=datetime.now()
    )

    block = (
        "```yaml\n"
        "┌─ REAL-TIME BANDWIDTH ───────────────────────────┐\n"
        f"│ ⬇️ Download Speed:  {net['download_speed_str']:<16}      │\n"
        f"│ ⬆️ Upload Speed:    {net['upload_speed_str']:<16}      │\n"
        "├─ TOTAL TRAFFIC ─────────────────────────────────┤\n"
        f"│ 📥 Received:        {net['bytes_recv_total_str']:<16}      │\n"
        f"│ 📤 Transferred:     {net['bytes_sent_total_str']:<16}      │\n"
        "└─────────────────────────────────────────────────┘\n"
        "```"
    )
    embed.description = block
    embed.set_footer(text="VPS Monitor Bot")
    return embed

def create_top_processes_embed(sort_by: str = "cpu") -> discord.Embed:
    """Build embed listing top processes consuming CPU or RAM."""
    procs = get_top_processes(limit=10, sort_by=sort_by)
    title_metric = "CPU" if sort_by.lower() == "cpu" else "RAM"

    embed = discord.Embed(
        title=f"🔥 TOP 10 PROCESSES BY {title_metric} USAGE",
        color=COLOR_INFO,
        timestamp=datetime.now()
    )

    table_data = []
    for p in procs:
        name = p['name'][:14]
        table_data.append([p['pid'], name, p['user'][:8], f"{p['cpu_percent']:.1f}%", f"{p['mem_percent']:.1f}%"])

    headers = ["PID", "NAME", "USER", "CPU%", "RAM%"]
    table_str = tabulate(table_data, headers=headers, tablefmt="simple")

    embed.description = f"```yaml\n{table_str}\n```"
    embed.set_footer(text="VPS Monitor Bot")
    return embed

def create_alert_embed(resource: str, current_val: float, threshold_val: float) -> discord.Embed:
    """Build high priority alert notification embed."""
    bar = make_ascii_bar(current_val, length=20)
    embed = discord.Embed(
        title=f"🚨 RESOURCE ALERT: High {resource} Usage!",
        description=(
            f"```yaml\n"
            f"CRITICAL: {resource} usage has exceeded safety threshold!\n"
            f"Current: [{bar}] {current_val:.1f}%\n"
            f"Limit:   {threshold_val:.1f}%\n"
            f"```"
        ),
        color=COLOR_DANGER,
        timestamp=datetime.now()
    )
    embed.set_footer(text="Automated VPS Resource Monitor Alert")
    return embed

# Alias for backwards compatibility
create_system_overview_embed = create_btop_dashboard_embed
