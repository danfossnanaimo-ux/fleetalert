import json
import os
import datetime as dt
from pathlib import Path
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from sheets_reader import get_today_roster

# Load bot token from environment
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Railway will store this file in its container filesystem
CHECKINS_FILE = Path("checkins.json")


def load_checkins() -> Dict:
    if CHECKINS_FILE.exists():
        with CHECKINS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkins(data: Dict):
    with CHECKINS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point when user starts the bot or scans QR."""
    today = dt.date.today().isoformat()
    roster = get_today_roster()
    names = [r["name"] for r in roster]

    if not names:
        await update.message.reply_text("No roster found for today.")
        return

    # Build buttons
    keyboard = []
    row = []
    for i, name in enumerate(names, start=1):
        row.append(InlineKeyboardButton(name, callback_data=f"checkin:{name}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Who is using this phone today?",
        reply_markup=reply_markup,
    )


async def handle_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("checkin:"):
        return

    name = data.split("checkin:", 1)[1]
    chat_id = query.message.chat_id
    today = dt.date.today().isoformat()

    checkins = load_checkins()
    if today not in checkins:
        checkins[today] = {}
    checkins[today][name] = chat_id
    save_checkins(checkins)

    await query.edit_message_text(
        text=f"Got it. This device is now mapped to: {name} for {today}."
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_checkin))

    # Railway supports polling just fine
    app.run_polling()


if __name__ == "__main__":
    main()
