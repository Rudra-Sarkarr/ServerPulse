// Clean, Light & Understandable Web Dashboard Client Script

let cpuRamChart = null;
let netChart = null;
let currentSortBy = "cpu";
let processesCache = [];

const MAX_HISTORY = 20;
const historyLabels = [];
const cpuDataPoints = [];
const ramDataPoints = [];
const netDownDataPoints = [];
const netUpDataPoints = [];

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    setupEventListeners();
    
    // Poll metrics every 2 seconds
    fetchDashboardData();
    setInterval(fetchDashboardData, 2000);
});

function initCharts() {
    // 1. CPU & RAM Chart
    const ctxCpuRam = document.getElementById("cleanCpuRamChart").getContext("2d");
    cpuRamChart = new Chart(ctxCpuRam, {
        type: "line",
        data: {
            labels: historyLabels,
            datasets: [
                {
                    label: "CPU Usage (%)",
                    data: cpuDataPoints,
                    borderColor: "#7c3aed",
                    backgroundColor: "rgba(124, 58, 237, 0.08)",
                    borderWidth: 2.5,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3
                },
                {
                    label: "Memory Usage (%)",
                    data: ramDataPoints,
                    borderColor: "#059669",
                    backgroundColor: "rgba(5, 150, 105, 0.08)",
                    borderWidth: 2.5,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: "#f1f5f9" },
                    ticks: { color: "#64748b", font: { family: "Plus Jakarta Sans" } }
                },
                x: {
                    grid: { color: "#f1f5f9" },
                    ticks: { color: "#64748b", font: { family: "Plus Jakarta Sans" } }
                }
            },
            plugins: {
                legend: { labels: { color: "#0f172a", font: { family: "Plus Jakarta Sans", weight: "600" } } }
            }
        }
    });

    // 2. Network Chart
    const ctxNet = document.getElementById("cleanNetChart").getContext("2d");
    netChart = new Chart(ctxNet, {
        type: "line",
        data: {
            labels: historyLabels,
            datasets: [
                {
                    label: "Download (KB/s)",
                    data: netDownDataPoints,
                    borderColor: "#2563eb",
                    backgroundColor: "rgba(37, 99, 235, 0.08)",
                    borderWidth: 2.5,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3
                },
                {
                    label: "Upload (KB/s)",
                    data: netUpDataPoints,
                    borderColor: "#ea580c",
                    backgroundColor: "rgba(234, 88, 12, 0.08)",
                    borderWidth: 2.5,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "#f1f5f9" },
                    ticks: { color: "#64748b", font: { family: "Plus Jakarta Sans" } }
                },
                x: {
                    grid: { color: "#f1f5f9" },
                    ticks: { color: "#64748b", font: { family: "Plus Jakarta Sans" } }
                }
            },
            plugins: {
                legend: { labels: { color: "#0f172a", font: { family: "Plus Jakarta Sans", weight: "600" } } }
            }
        }
    });
}

function setupEventListeners() {
    document.getElementById("btn-manual-refresh").addEventListener("click", fetchDashboardData);

    document.getElementById("btn-sort-cpu").addEventListener("click", () => {
        currentSortBy = "cpu";
        document.getElementById("btn-sort-cpu").classList.add("active");
        document.getElementById("btn-sort-mem").classList.remove("active");
        fetchProcesses();
    });

    document.getElementById("btn-sort-mem").addEventListener("click", () => {
        currentSortBy = "ram";
        document.getElementById("btn-sort-mem").classList.add("active");
        document.getElementById("btn-sort-cpu").classList.remove("active");
        fetchProcesses();
    });

    document.getElementById("proc-search").addEventListener("input", renderProcessesTable);

    document.getElementById("btn-test-alert").addEventListener("click", async () => {
        if (!confirm("Send a test alert message to your Discord channel?")) return;
        try {
            const res = await fetch("/api/bot/test-alert", { method: "POST" });
            const data = await res.json();
            alert(data.message || "Test alert sent!");
        } catch (err) {
            alert("Error: " + err.message);
        }
    });
}

async function fetchDashboardData() {
    await Promise.all([
        fetchMetrics(),
        fetchBotStatus(),
        fetchProcesses()
    ]);
}

async function fetchMetrics() {
    try {
        const res = await fetch("/api/metrics");
        if (!res.ok) return;
        const data = await res.json();

        // Server Sub Header
        document.getElementById("server-info-sub").textContent = `${data.system.hostname} • ${data.system.os} • Uptime: ${data.system.uptime}`;

        // CPU Card
        const cpuPct = data.cpu.total_percent;
        document.getElementById("cpu-badge").textContent = `${cpuPct.toFixed(1)}%`;
        document.getElementById("cpu-main-val").textContent = `${cpuPct.toFixed(1)}%`;
        document.getElementById("cpu-cores-str").textContent = `${data.cpu.physical_cores} Physical / ${data.cpu.logical_cores} Logical Cores`;
        document.getElementById("cpu-bar-fill").style.width = `${cpuPct}%`;
        document.getElementById("cpu-load-str").textContent = `Load Averages (1m, 5m, 15m): ${data.cpu.load_1} • ${data.cpu.load_5} • ${data.cpu.load_15}`;

        // RAM Card
        const ramPct = data.ram.percent;
        document.getElementById("ram-badge").textContent = `${ramPct.toFixed(1)}%`;
        document.getElementById("ram-used-str").textContent = data.ram.used_str;
        document.getElementById("ram-total-str").textContent = `/ ${data.ram.total_str}`;
        document.getElementById("ram-bar-fill").style.width = `${ramPct}%`;
        document.getElementById("ram-free-str").textContent = `Free: ${data.ram.free_str} • Available: ${data.ram.available_str}`;

        // Storage Card
        const diskPct = data.disk.root_percent;
        document.getElementById("disk-badge").textContent = `${diskPct.toFixed(1)}%`;
        document.getElementById("disk-used-str").textContent = data.disk.root_used_str;
        document.getElementById("disk-total-str").textContent = `/ ${data.disk.root_total_str}`;
        document.getElementById("disk-bar-fill").style.width = `${diskPct}%`;
        document.getElementById("disk-free-str").textContent = `Free Storage: ${data.disk.root_free_str}`;

        // Network Card
        document.getElementById("net-down-speed").textContent = data.network.download_speed_str;
        document.getElementById("net-up-speed").textContent = data.network.upload_speed_str;
        document.getElementById("net-total-str").textContent = `Total Recv: ${data.network.bytes_recv_total_str} • Sent: ${data.network.bytes_sent_total_str}`;

        // Update Charts
        const timeLabel = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        const parseSpeedKBs = (sStr) => {
            if (!sStr) return 0;
            const p = sStr.split(" ");
            const v = parseFloat(p[0]) || 0;
            const u = p[1] ? p[1].toUpperCase() : "B/S";
            if (u.startsWith("MB")) return v * 1024;
            if (u.startsWith("KB")) return v;
            return v / 1024;
        };

        const downKBs = parseSpeedKBs(data.network.download_speed_str);
        const upKBs = parseSpeedKBs(data.network.upload_speed_str);

        pushChartData(timeLabel, cpuPct, ramPct, downKBs, upKBs);

    } catch (err) {
        console.error("Metrics error:", err);
    }
}

function pushChartData(timeLabel, cpuVal, ramVal, downKBs, upKBs) {
    if (historyLabels.length >= MAX_HISTORY) {
        historyLabels.shift();
        cpuDataPoints.shift();
        ramDataPoints.shift();
        netDownDataPoints.shift();
        netUpDataPoints.shift();
    }

    historyLabels.push(timeLabel);
    cpuDataPoints.push(cpuVal);
    ramDataPoints.push(ramVal);
    netDownDataPoints.push(downKBs.toFixed(1));
    netUpDataPoints.push(upKBs.toFixed(1));

    cpuRamChart.update();
    netChart.update();
}

async function fetchBotStatus() {
    try {
        const res = await fetch("/api/bot/status");
        if (!res.ok) return;
        const bot = await res.json();

        const nameEl = document.getElementById("bot-status-name");
        const pillEl = document.getElementById("bot-status-pill");

        if (bot.online) {
            nameEl.textContent = `Discord Bot Connected (${bot.name})`;
            pillEl.className = "bot-pill online";
            document.getElementById("bot-info-name").textContent = bot.name;
            document.getElementById("bot-info-ping").textContent = bot.ping_ms ? `${bot.ping_ms} ms` : "N/A";
        } else {
            nameEl.textContent = "Discord Bot Offline";
            pillEl.className = "bot-pill offline";
            document.getElementById("bot-info-name").textContent = "Offline";
            document.getElementById("bot-info-ping").textContent = "N/A";
        }
    } catch (err) {
        console.error("Bot status error:", err);
    }
}

async function fetchProcesses() {
    try {
        const res = await fetch(`/api/processes?sort_by=${currentSortBy}&limit=25`);
        if (!res.ok) return;
        const data = await res.json();
        processesCache = data.processes || [];
        renderProcessesTable();
    } catch (err) {
        console.error("Processes error:", err);
    }
}

function renderProcessesTable() {
    const search = document.getElementById("proc-search").value.toLowerCase().trim();
    const tbody = document.getElementById("proc-rows");

    const filtered = processesCache.filter(p => 
        p.name.toLowerCase().includes(search) || 
        String(p.pid).includes(search) ||
        p.user.toLowerCase().includes(search)
    );

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No processes matching "${search}"</td></tr>`;
        return;
    }

    let rows = "";
    filtered.forEach(p => {
        rows += `
            <tr>
                <td><code>${p.pid}</code></td>
                <td><strong style="color:#0f172a;">${escapeHtml(p.name)}</strong></td>
                <td><span style="color:#64748b;">${escapeHtml(p.user)}</span></td>
                <td><span class="kpi-badge ${p.cpu_percent > 40 ? 'cpu-badge' : 'ram-badge'}">${p.cpu_percent.toFixed(1)}%</span></td>
                <td>${p.mem_percent.toFixed(1)}%</td>
                <td>${p.mem_bytes_str}</td>
            </tr>
        `;
    });
    tbody.innerHTML = rows;
}

function escapeHtml(str) {
    return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
