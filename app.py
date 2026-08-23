"""
Network Monitoring Dashboard
-----------------------------
A lightweight Flask app that:
  - Samples system-wide network throughput (bytes sent/recv) every second
    using psutil, and derives an up/down speed in Mbps.
  - Pings a configurable list of hosts on a timer to track latency and
    uptime, and logs state transitions (host went down / came back up).
  - Exposes a small JSON API that the front-end dashboard polls.

Run with:  python app.py
Then open: http://localhost:5000
"""

import platform
import re
import subprocess
import threading
import time
from collections import deque
from datetime import datetime

import psutil
from flask import Flask, jsonify, render_template

from config import HOSTS, HISTORY_LENGTH, SAMPLE_INTERVAL_SECONDS, PING_TIMEOUT_SECONDS

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Shared in-memory state (guarded by a lock since it's written by the
# background monitor thread and read by Flask request threads).
# ---------------------------------------------------------------------------
state_lock = threading.Lock()

state = {
    "bandwidth_history": deque(maxlen=HISTORY_LENGTH),   # [{t, down_mbps, up_mbps}]
    "latency_history": {h: deque(maxlen=HISTORY_LENGTH) for h in HOSTS},  # per host [{t, ms}]
    "hosts": {
        h: {
            "host": h,
            "status": "unknown",   # "up" | "down" | "unknown"
            "latency_ms": None,
            "checks": 0,
            "successful_checks": 0,
            "last_change": None,
        }
        for h in HOSTS
    },
    "events": deque(maxlen=100),   # [{t, message, level}]
    "system": {
        "cpu_percent": 0,
        "mem_percent": 0,
        "hostname": platform.node(),
    },
}


def log_event(message, level="info"):
    state["events"].appendleft(
        {"t": datetime.now().strftime("%H:%M:%S"), "message": message, "level": level}
    )


def ping_host(host):
    """Ping a host once and return latency in ms, or None if unreachable.
    Works on Windows, macOS and Linux by adjusting the ping flags."""
    count_flag = "-n" if platform.system().lower() == "windows" else "-c"
    timeout_flag = "-w" if platform.system().lower() == "windows" else "-W"
    timeout_val = str(int(PING_TIMEOUT_SECONDS * 1000)) if platform.system().lower() == "windows" else str(PING_TIMEOUT_SECONDS)

    cmd = ["ping", count_flag, "1", timeout_flag, timeout_val, host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=PING_TIMEOUT_SECONDS + 2)
        if result.returncode != 0:
            return None
        match = re.search(r"time[=<]([\d.]+)\s*ms", result.stdout, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 0.0  # replied but couldn't parse latency
    except Exception:
        return None


def monitor_hosts():
    while True:
        for host in HOSTS:
            latency = ping_host(host)
            with state_lock:
                info = state["hosts"][host]
                was_up = info["status"] == "up"
                info["checks"] += 1
                info["latency_ms"] = latency
                now_iso = datetime.now().strftime("%H:%M:%S")

                if latency is not None:
                    info["successful_checks"] += 1
                    if not was_up:
                        info["last_change"] = now_iso
                        if info["status"] != "unknown":
                            log_event(f"{host} is back UP ({latency:.0f} ms)", "up")
                    info["status"] = "up"
                    state["latency_history"][host].append(
                        {"t": now_iso, "ms": round(latency, 1)}
                    )
                else:
                    if was_up or info["status"] == "unknown":
                        info["last_change"] = now_iso
                        if info["status"] != "unknown":
                            log_event(f"{host} is DOWN (no reply)", "down")
                    info["status"] = "down"
                    state["latency_history"][host].append({"t": now_iso, "ms": None})
        time.sleep(SAMPLE_INTERVAL_SECONDS)


def monitor_bandwidth():
    prev = psutil.net_io_counters()
    prev_time = time.time()
    while True:
        time.sleep(1)
        curr = psutil.net_io_counters()
        curr_time = time.time()
        elapsed = max(curr_time - prev_time, 1e-6)

        down_mbps = ((curr.bytes_recv - prev.bytes_recv) * 8 / elapsed) / 1_000_000
        up_mbps = ((curr.bytes_sent - prev.bytes_sent) * 8 / elapsed) / 1_000_000

        with state_lock:
            state["bandwidth_history"].append(
                {
                    "t": datetime.now().strftime("%H:%M:%S"),
                    "down_mbps": round(max(down_mbps, 0), 3),
                    "up_mbps": round(max(up_mbps, 0), 3),
                }
            )
            state["system"]["cpu_percent"] = psutil.cpu_percent(interval=None)
            state["system"]["mem_percent"] = psutil.virtual_memory().percent

        prev, prev_time = curr, curr_time


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", hosts=HOSTS)


@app.route("/api/summary")
def api_summary():
    with state_lock:
        bandwidth = list(state["bandwidth_history"])
        hosts = list(state["hosts"].values())
        events = list(state["events"])
        system = dict(state["system"])
        latency_history = {
            h: list(v) for h, v in state["latency_history"].items()
        }

    up_count = sum(1 for h in hosts if h["status"] == "up")
    down_count = sum(1 for h in hosts if h["status"] == "down")

    return jsonify(
        {
            "system": system,
            "bandwidth_history": bandwidth,
            "current": bandwidth[-1] if bandwidth else {"down_mbps": 0, "up_mbps": 0},
            "hosts": hosts,
            "latency_history": latency_history,
            "events": events,
            "summary": {
                "up": up_count,
                "down": down_count,
                "total": len(hosts),
            },
        }
    )


if __name__ == "__main__":
    threading.Thread(target=monitor_bandwidth, daemon=True).start()
    threading.Thread(target=monitor_hosts, daemon=True).start()
    log_event("Network Monitoring Dashboard started", "info")
    app.run(host="0.0.0.0", port=5000, debug=False)
