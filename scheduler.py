import os
import json
import datetime as dt
from pathlib import Path
from typing import Dict, List, Optional

import pytz
import requests

from sheets_reader import get_today_roster

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHECKINS_FILE = Path("checkins.json")
SENT_FILE = Path("sent_alerts.json")
TIMEZONE = os.environ.get("FLEETALERT_TZ", "America/Vancouver")


def load_json(path: Path) -> Dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: Dict):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def parse_time(time_str: Optional[str], tz) -> Optional[dt.datetime]:
    if not time_str:
        return None
    # Expect something like "08:30" or "8:30"
    try:
        hour, minute = [int(x) for x in time_str.split(":")]
    except Exception:
        return None
    today = dt.date.today()
    local_dt = tz.localize(dt.datetime(today.year, today.month, today.day, hour, minute))
    return local_dt


def send_telegram_message(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": text})
    resp.raise_for_status()


def main():
    tz = pytz.timezone(TIMEZONE)
    now = dt.datetime.now(tz)
    today_str = dt.date.today().isoformat()

    roster = get_today_roster()
    checkins = load_json(CHECKINS_FILE)
    sent = load_json(SENT_FILE)

    if today_str not in checkins:
        print("No check-ins for today; nothing to send.")
        return

    today_checkins = checkins[today_str]
    if today_str not in sent:
        sent[today_str] = []

    for entry in roster:
        name = entry["name"]
        time_str = entry.get("time")
        if name not in today_checkins:
            continue  # no device mapped

        alert_time = parse_time(time_str, tz)
        if alert_time is None:
            continue

        # Add 4 hours
        alert_time = alert_time + dt.timedelta(hours=4)

        # If already sent, skip
        key = f"{name}@{alert_time.isoformat()}"
        if key in sent[today_str]:
            continue

        # Send if within past 10 minutes or next 5 minutes (tunable window)
        delta = now - alert_time
        if dt.timedelta(minutes=-5) <= delta <= dt.timedelta(minutes=10):
            chat_id = today_checkins[name]
            text = f"Reminder for {name}: your scheduled time was {time_str}, alert +4h is now."
            try:
                send_telegram_message(chat_id, text)
                sent[today_str].append(key)
                print(f"Sent alert to {name} ({chat_id}) at {now.isoformat()}")
            except Exception as e:
                print(f"Failed to send alert to {name}: {e}")

    save_json(SENT_FILE, sent)


if __name__ == "__main__":
    main()
