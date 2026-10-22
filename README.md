# 🖥️ System Monitor

![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

A containerized system monitor that watches the **host machine's** CPU, RAM, and disk usage, and sends a Telegram alert whenever any of them crosses a threshold. Built to run continuously as a Docker service, with restart resilience and persistent error logging.

## ✨ Features

- 📊 **Live resource monitoring** — CPU, RAM, and disk usage, checked every 2 seconds
- 📲 **Telegram alerts** — get notified the moment a resource crosses 80% usage, and again when it recovers
- 🔕 **Alert deduplication** — no spam: an alert only fires on a state change (normal → warning, or warning → normal), not on every check
- 🐳 **True host monitoring from a container** — mounts the host's `/proc` and root filesystem (read-only) so the numbers reflect the actual machine, not just the container's own limited view
- 🔁 **Self-healing** — configured with `restart: unless-stopped`, so the monitor comes back up automatically after a crash or host reboot
- 📁 **Persistent error logs** — connection/API failures are written to a log file on the host (survives container restarts) and also to stderr for live `docker logs` visibility

## 🧠 Why host mounting matters

By default, a Docker container is isolated from the host — a monitoring tool running inside one would only see the container's own tiny resource footprint, not the real machine's. This project solves that by mounting the host's `/proc` and `/` into the container as read-only volumes, and pointing `psutil` at those paths instead of the container's own. This is the same technique used by production monitoring agents like Prometheus's Node Exporter.

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/RissDevSec/system-monitor.git
cd system-monitor
```

### 2. Set up your Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram and create a new bot to get a **bot token**.
2. Send any message to your new bot, then visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` to find your **chat ID**.

### 3. Configure environment variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

```dotenv
BOT_KEY=your_telegram_bot_token_here
CHAT_ID=your_telegram_chat_id_here
PROCFS_PATH=/host/proc
DISK_PATH=/host/root
```

`PROCFS_PATH` and `DISK_PATH` should stay as shown above — they point to where the host's filesystem is mounted *inside the container* (see `docker-compose.yaml`).

### 4. Build and run

```bash
docker compose up --build -d
```

### 5. Watch the logs

```bash
docker compose logs -f system-monitor
```

To see only errors (filtering out the routine status lines):

```bash
docker compose logs system-monitor 2>&1 1>/dev/null
```

### Stopping the monitor

```bash
docker compose down
```

## 📖 Example output

```
System monitor started. Checking every 2 seconds. Press Ctrl+C to stop.
[2026-09-02 09:03:32] CPU: 9% | RAM: 82% (6.1/7.5 GB) ⚠ WARNING | Disk: 55%

[2026-09-02 09:03:34] CPU: 13% | RAM: 83% (6.2/7.5 GB) ⚠ WARNING | Disk: 55%
```

When RAM first crosses 80%, a single Telegram alert is sent (`⚠ WARNING - RAM almost full!`). No further alerts are sent while it stays above 80% — only when it drops back down (`✓ INFO - RAM back to normal`) or crosses the threshold again later.

## 🧪 Testing the Telegram connection

You can test your bot credentials independently, without running the full monitor:

```bash
docker compose run --rm system-monitor python notifier.py
```

## 🛠️ Tech Stack

- Python 3.12
- [psutil](https://github.com/giampaolo/psutil) — system resource stats
- [requests](https://requests.readthedocs.io/) — Telegram Bot API calls
- Docker & Docker Compose

## 📁 Project Structure

```
system-monitor/
├── main.py              # Monitoring loop and threshold logic
├── notifier.py          # Telegram notifications and error logging
├── logs/                # Persisted error logs (gitignored)
├── requirements.txt
├── Dockerfile
├── docker-compose.yaml
├── .env.example
├── README.md
└── LICENSE
```

## ⚠️ Security note

The container mounts the host's root filesystem read-only to enable disk monitoring. This is a common, accepted pattern for host-monitoring tools (the same one used by Node Exporter), but it does mean the container can read any file on the host. Keep the image's dependencies minimal and up to date, and never expose this container's ports to the public internet.

## 📄 License

This project is licensed under the [MIT License](LICENSE) — feel free to use, modify, and distribute it.