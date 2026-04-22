# Tesla Model Y Germany Inventory Monitor

Polls the Tesla DE inventory API every minute and sends a Telegram message + email whenever a new Model Y appears.

## Setup

### 1. Clone and configure

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Your chat/user ID – get it from [@userinfobot](https://t.me/userinfobot) |
| `SMTP_USER` | Your Gmail address |
| `SMTP_PASS` | A Gmail [App Password](https://myaccount.google.com/apppasswords) (not your regular password) |

### 2. Run

```bash
docker compose up -d
```

Logs:

```bash
docker compose logs -f
```

Stop:

```bash
docker compose down
```

## How it works

- Hits the Tesla inventory API for new Model Y listings in Germany every 60 seconds
- Tracks seen VINs in a persistent Docker volume (`/data/seen_vins.json`) so you only get alerted once per car
- On a new listing: sends a Telegram message and an email with the direct car link + referral bonus link

## Referral link

Every alert includes: <https://www.mydealz.de/visit/referralclaim/32931>
