# NETWATCH — Network Monitoring Dashboard

A self-hosted, real-time network monitoring dashboard. It tracks:

- **Bandwidth throughput** — live upload/download Mbps, sampled every second
- **Host uptime & latency** — pings a configurable list of hosts and tracks
  status transitions, latency, and uptime %
- **System load** — CPU and memory usage
- **Event log** — a running log of host-down / host-recovered events

Built with a Flask backend (no database required — everything lives in
memory) and a dependency-light vanilla JS + Chart.js frontend.

![status](https://img.shields.io/badge/status-active-56d97a)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

## Features

- Live bandwidth chart (download/upload, Mbps)
- Per-host latency chart with color-coded lines
- Host status table with uptime percentage
- Scrolling event log for down/recovery events
- Cross-platform ping (Windows / macOS / Linux)
- Zero external services — runs entirely on your machine
- Polls a JSON API every 3 seconds — no WebSocket setup needed

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/network-monitoring-dashboard.git
cd network-monitoring-dashboard

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run it
python app.py
```

Then open **http://localhost:5000** in your browser.

## Configuration

Edit `config.py` to change what's monitored:

```python
HOSTS = [
    "1.1.1.1",
    "8.8.8.8",
    "google.com",
]

HISTORY_LENGTH = 60             # samples kept for charts
SAMPLE_INTERVAL_SECONDS = 3     # seconds between ping rounds
PING_TIMEOUT_SECONDS = 1        # per-ping timeout
```

Add any host, IP, gateway, or internal server you want to track uptime and
latency for.

## Project structure

```
network-monitoring-dashboard/
├── app.py                  # Flask app + background monitor threads
├── config.py                # Hosts and timing configuration
├── requirements.txt
├── static/
│   ├── css/style.css        # Dashboard styling
│   └── js/dashboard.js      # Polling + Chart.js rendering
├── templates/
│   └── index.html           # Dashboard layout
├── LICENSE
└── README.md
```

## How it works

- A background thread samples `psutil.net_io_counters()` once a second and
  derives Mbps from the delta in bytes sent/received.
- A second background thread pings each configured host on a timer using the
  system `ping` command (parsed for latency), and records status transitions
  to the event log.
- The Flask route `GET /api/summary` returns the current snapshot (system
  stats, bandwidth history, host statuses, latency history, recent events) as
  JSON.
- The frontend polls that endpoint every 3 seconds and updates two Chart.js
  line charts, a host status table, and the event log — no page reloads.

## Pushing this to GitHub

If you're starting from these files, initialize a repo and push:

```bash
git init
git add .
git commit -m "Initial commit: Network Monitoring Dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/network-monitoring-dashboard.git
git push -u origin main
```

## Extending it

- **Alerting**: hook `log_event()` in `app.py` up to email/Slack/webhook calls
  when a host goes down.
- **Persistence**: swap the in-memory `deque` history for SQLite/Postgres if
  you want history to survive restarts.
- **More metrics**: `psutil` also exposes per-interface stats, connection
  counts, and packet loss — easy to add more panels.
- **Auth**: put this behind a reverse proxy (nginx/Caddy) with basic auth if
  you're exposing it beyond localhost.

## License

MIT — see [LICENSE](LICENSE).
