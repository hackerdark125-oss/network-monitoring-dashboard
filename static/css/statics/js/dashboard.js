/* NETWATCH dashboard client
   Polls /api/summary and renders bandwidth + latency charts,
   the host status table, and the scrolling event log. */

const POLL_MS = 3000;

const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 250 },
  scales: {
    x: {
      ticks: { color: '#3c4a56', maxTicksLimit: 6, font: { family: 'JetBrains Mono', size: 9 } },
      grid: { color: 'rgba(255,255,255,0.04)' },
    },
    y: {
      ticks: { color: '#3c4a56', font: { family: 'JetBrains Mono', size: 9 } },
      grid: { color: 'rgba(255,255,255,0.04)' },
      beginAtZero: true,
    },
  },
  plugins: { legend: { display: false } },
  elements: { point: { radius: 0 }, line: { tension: 0.3, borderWidth: 2 } },
};

const bandwidthCtx = document.getElementById('bandwidthChart').getContext('2d');
const bandwidthChart = new Chart(bandwidthCtx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label: 'Download', data: [], borderColor: '#4fc3e8', backgroundColor: 'rgba(79,195,232,0.08)', fill: true },
      { label: 'Upload', data: [], borderColor: '#5b9ef5', backgroundColor: 'rgba(91,158,245,0.06)', fill: true },
    ],
  },
  options: chartDefaults,
});

const latencyCtx = document.getElementById('latencyChart').getContext('2d');
const latencyColors = ['#56d97a', '#e8a33d', '#4fc3e8', '#f0554a', '#5b9ef5'];
const latencyChart = new Chart(latencyCtx, {
  type: 'line',
  data: { labels: [], datasets: [] },
  options: {
    ...chartDefaults,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: { color: '#5c7080', font: { family: 'JetBrains Mono', size: 9 }, boxWidth: 8, boxHeight: 8 },
      },
    },
  },
});

let latencyDatasetsInitialized = false;

function updateClock() {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

function renderHostTable(hosts) {
  const body = document.getElementById('host-table-body');
  body.innerHTML = '';
  hosts.forEach((h) => {
    const uptimePct = h.checks > 0 ? ((h.successful_checks / h.checks) * 100).toFixed(1) : '--';
    const statusClass = h.status === 'up' ? 'status-up' : h.status === 'down' ? 'status-down' : 'status-unknown';
    const latencyClass = h.status === 'down' ? 'host-latency down' : 'host-latency';
    const latencyText = h.latency_ms != null ? `${h.latency_ms.toFixed(0)} ms` : '--';

    const row = document.createElement('tr');
    row.innerHTML = `
      <td><span class="status-dot ${statusClass}"></span></td>
      <td class="host-name">${h.host}</td>
      <td class="${latencyClass}">${latencyText}</td>
      <td class="host-uptime">${uptimePct}%</td>
    `;
    body.appendChild(row);
  });
}

function renderLog(events) {
  const body = document.getElementById('log-body');
  body.innerHTML = '';
  // column-reverse means first child renders at bottom; append newest first
  events.forEach((e) => {
    const line = document.createElement('div');
    line.className = `log-line level-${e.level}`;
    line.innerHTML = `<span class="log-time">${e.t}</span>${e.message}`;
    body.appendChild(line);
  });
}

function ensureLatencyDatasets(hostNames) {
  if (latencyDatasetsInitialized) return;
  latencyChart.data.datasets = hostNames.map((name, i) => ({
    label: name,
    data: [],
    borderColor: latencyColors[i % latencyColors.length],
    spanGaps: true,
  }));
  latencyDatasetsInitialized = true;
}

async function poll() {
  try {
    const res = await fetch('/api/summary');
    const data = await res.json();

    // top bar chips
    document.getElementById('cpu-value').textContent = `${data.system.cpu_percent.toFixed(0)}%`;
    document.getElementById('mem-value').textContent = `${data.system.mem_percent.toFixed(0)}%`;
    document.getElementById('hosts-value').textContent = `${data.summary.up}/${data.summary.total}`;
    document.getElementById('hostname-label').textContent = data.system.hostname;

    // speed readout
    document.getElementById('down-speed').textContent = data.current.down_mbps.toFixed(2);
    document.getElementById('up-speed').textContent = data.current.up_mbps.toFixed(2);

    // bandwidth chart
    const bw = data.bandwidth_history;
    bandwidthChart.data.labels = bw.map((p) => p.t);
    bandwidthChart.data.datasets[0].data = bw.map((p) => p.down_mbps);
    bandwidthChart.data.datasets[1].data = bw.map((p) => p.up_mbps);
    bandwidthChart.update('none');

    // latency chart
    const hostNames = Object.keys(data.latency_history);
    ensureLatencyDatasets(hostNames);
    const anyHostHistory = data.latency_history[hostNames[0]] || [];
    latencyChart.data.labels = anyHostHistory.map((p) => p.t);
    hostNames.forEach((name, i) => {
      latencyChart.data.datasets[i].data = data.latency_history[name].map((p) => p.ms);
    });
    latencyChart.update('none');

    // host table + log
    renderHostTable(data.hosts);
    renderLog(data.events);
  } catch (err) {
    console.error('poll failed', err);
  }
}

poll();
setInterval(poll, POLL_MS);
