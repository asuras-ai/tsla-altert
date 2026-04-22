#!/usr/bin/env python3
import os
import json
import time
import logging
import smtplib
import requests
import cloudscraper
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

TESLA_API_URL = (
    "https://www.tesla.com/inventory/api/v4/inventory-results"
    "?query=%7B%22query%22%3A%7B%22model%22%3A%22my%22%2C%22condition%22%3A%22new%22%2C"
    "%22options%22%3A%7B%7D%2C%22arrangeby%22%3A%22Price%22%2C%22order%22%3A%22asc%22%2C"
    "%22market%22%3A%22DE%22%2C%22language%22%3A%22de%22%2C%22super_region%22%3A%22europe%22%2C"
    "%22lng%22%3A13.4%2C%22lat%22%3A52.5%2C%22zip%22%3A%2210115%22%2C%22range%22%3A0%2C"
    "%22region%22%3A%22DE%22%7D%2C%22offset%22%3A0%2C%22count%22%3A50%2C%22outsideOffset%22%3A0%2C"
    "%22outsideSearch%22%3Afalse%2C%22isFalconDeliverySelectionEnabled%22%3Afalse%2C"
    "%22version%22%3Anull%7D"
)

REFERRAL_LINK = "https://www.mydealz.de/visit/referralclaim/32931"
SEEN_FILE = "/data/seen_vins.json"

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]
EMAIL_TO = os.environ["EMAIL_TO"]

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))

_scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "linux", "mobile": False}
)


def load_seen() -> set:
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(vins: set) -> None:
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(list(vins), f)


def fetch_inventory() -> list:
    headers = {
        "Accept": "application/json",
        "Accept-Language": "de-DE,de;q=0.9",
        "Referer": "https://www.tesla.com/de_DE/inventory/new/my",
    }
    resp = _scraper.get(TESLA_API_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def car_url(vin: str) -> str:
    return f"https://www.tesla.com/de_DE/my/order/{vin}"


def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    log.info("Telegram message sent")


def send_email(subject: str, body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())
    log.info("Email sent to %s", EMAIL_TO)


def format_car_details(car: dict) -> str:
    trim = car.get("TrimName", "")
    color = car.get("PAINT", [""])[0] if car.get("PAINT") else ""
    interior = car.get("INTERIOR", [""])[0] if car.get("INTERIOR") else ""
    price = car.get("PurchasePrice", "")
    vin = car.get("VIN", "")
    odometer = car.get("Odometer", "")
    year = car.get("Year", "")

    parts = [p for p in [str(year), trim, color, interior] if p]
    description = " | ".join(parts)
    price_str = f"€{price:,.0f}" if isinstance(price, (int, float)) else str(price)

    return description, price_str, vin


def notify_new_cars(new_cars: list) -> None:
    for car in new_cars:
        description, price_str, vin = format_car_details(car)
        url = car_url(vin)

        telegram_text = (
            f"🚗 <b>Neues Tesla Model Y verfügbar!</b>\n\n"
            f"<b>{description}</b>\n"
            f"Preis: {price_str}\n"
            f"VIN: {vin}\n\n"
            f'<a href="{url}">Zum Fahrzeug</a>\n\n'
            f'<a href="{REFERRAL_LINK}">Bonus-Link aktivieren</a>'
        )

        email_body = f"""
        <html><body>
        <h2>Neues Tesla Model Y verfügbar!</h2>
        <p><strong>{description}</strong><br>
        Preis: {price_str}<br>
        VIN: {vin}</p>
        <p><a href="{url}">Zum Fahrzeug &rarr;</a></p>
        <p><a href="{REFERRAL_LINK}">Bonus-Link aktivieren &rarr;</a></p>
        </body></html>
        """

        email_subject = f"Tesla Model Y: {description} – {price_str}"

        try:
            send_telegram(telegram_text)
        except Exception as e:
            log.error("Telegram error: %s", e)

        try:
            send_email(email_subject, email_body)
        except Exception as e:
            log.error("Email error: %s", e)


def main() -> None:
    log.info("Tesla Model Y monitor starting (interval=%ds)", POLL_INTERVAL)
    seen = load_seen()
    log.info("Loaded %d known VINs", len(seen))

    while True:
        try:
            cars = fetch_inventory()
            log.info("Fetched %d cars from Tesla inventory", len(cars))

            current_vins = {car["VIN"] for car in cars if "VIN" in car}
            new_vins = current_vins - seen

            if new_vins:
                new_cars = [c for c in cars if c.get("VIN") in new_vins]
                log.info("Found %d new car(s): %s", len(new_cars), new_vins)
                notify_new_cars(new_cars)
                seen.update(new_vins)
                save_seen(seen)
            else:
                log.info("No new cars found")

        except requests.HTTPError as e:
            log.error("HTTP error fetching inventory: %s", e)
        except Exception as e:
            log.exception("Unexpected error: %s", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
