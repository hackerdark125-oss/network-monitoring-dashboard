"""
Configuration for the Network Monitoring Dashboard.
Edit HOSTS to the devices/servers you want to track.
"""

# Hosts to ping and track uptime/latency for.
# Use IPs or hostnames — e.g. your router, a gateway, a DNS server, a site.
HOSTS = [
    "1.1.1.1",        # Cloudflare DNS
    "8.8.8.8",        # Google DNS
    "google.com",
]

# How many samples to keep for charts (60 samples ≈ last few minutes
# depending on SAMPLE_INTERVAL_SECONDS).
HISTORY_LENGTH = 60

# Seconds between each round of host pings.
SAMPLE_INTERVAL_SECONDS = 3

# Seconds to wait for a single ping reply before marking it a timeout.
PING_TIMEOUT_SECONDS = 1
