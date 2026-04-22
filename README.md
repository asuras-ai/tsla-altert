# Tesla Model Y Germany Inventory Monitor

Watches the Tesla DE new-car inventory every 60 seconds. When a Model Y appears that hasn't been seen before, it fires a Telegram message and an HTML email with a direct link to the car and a referral bonus link.

## Requirements

- Docker and Docker Compose
- A Telegram bot (free, takes 2 minutes to create)
- A Gmail account with an App Password enabled

## Quick start

```bash
git clone https://github.com/asuras-ai/tsla-altert.git
cd tsla-altert
cp .env.example .env
# fill in .env (see Configuration below)
docker compose up -d
```

## Configuration

All settings live in `.env` (never committed). Copy `.env.example` as a starting point.

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | – | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | yes | – | Your numeric user/chat ID – get it from [@userinfobot](https://t.me/userinfobot) |
| `SMTP_USER` | yes | – | Gmail address used to send alerts |
| `SMTP_PASS` | yes | – | Gmail [App Password](https://myaccount.google.com/apppasswords) (not your login password) |
| `EMAIL_TO` | yes | – | Recipient email address for alerts |
| `SMTP_HOST` | no | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | no | `587` | SMTP port (STARTTLS) |
| `POLL_INTERVAL` | no | `60` | Seconds between inventory checks |

### Getting a Telegram bot token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token that looks like `123456789:AAxxxxxxx…`

### Getting your Telegram chat ID

1. Open Telegram and search for **@userinfobot**
2. Send `/start` — it replies with your numeric ID
3. Use that number as `TELEGRAM_CHAT_ID`

### Getting a Gmail App Password

Gmail requires an App Password when 2-Step Verification is enabled (which it must be):

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Create a new app password (name it anything, e.g. "Tesla Monitor")
3. Copy the 16-character password into `SMTP_PASS`

## Docker Compose

```bash
# Start in the background
docker compose up -d

# Follow logs
docker compose logs -f

# Stop
docker compose down

# Rebuild after code changes
docker compose up -d --build
```

The container restarts automatically unless explicitly stopped (`restart: unless-stopped`).

Seen VINs are stored in a named Docker volume (`tesla-data`) mounted at `/data/seen_vins.json` inside the container, so state survives restarts and container rebuilds.

## How it works

1. Every `POLL_INTERVAL` seconds the monitor calls the Tesla inventory API for new Model Y listings in Germany (market `DE`, sorted by price ascending).
2. Each result's VIN is compared against the set of already-seen VINs loaded from disk.
3. For every unseen VIN a Telegram message and an HTML email are sent, each containing:
   - Year, trim, colour, interior
   - Price in EUR
   - Direct link to the car on tesla.com
   - Referral bonus link: <https://www.mydealz.de/visit/referralclaim/32931>
4. The new VINs are appended to the seen set and persisted to disk so no duplicate alerts are sent.

Errors from Telegram or the mail server are logged but do not crash the loop — the monitor keeps running.

## Project structure

```
.
├── monitor.py          # main polling loop + notification logic
├── Dockerfile          # Python 3.12-slim image
├── docker-compose.yml  # service definition with persistent volume
├── requirements.txt    # requests
├── .env.example        # configuration template (no secrets)
└── .gitignore          # excludes .env
```
