import os
import json
import datetime as dt
from typing import List, Dict

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Sheet ID for your roster
ROSTER_SHEET_ID = os.environ.get("ROSTER_SHEET_ID", "1kAantOHhTF3D9iZPxn1gtxZ7QcCwoZyiTyjsSQMp8Bo")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def get_sheets_service():
    sa_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def pick_today_tab_title(sheet_metadata: dict) -> str:
    """Very simple strategy: if a tab title exactly matches today's YYYY-MM-DD, use it;
    otherwise fall back to the first sheet. Adjust this to match your naming convention."""
    today = dt.date.today()
    today_str = today.strftime("%Y-%m-%d")

    sheets = sheet_metadata["sheets"]
    titles = [s["properties"]["title"] for s in sheets]

    for t in titles:
        if t.strip() == today_str:
            return t

    # Fallback: first sheet
    return titles[0]


def get_today_roster() -> List[Dict]:
    """Return a list of dicts: [{'name': 'Alex M.', 'time': '08:30'}, ...]"""
    service = get_sheets_service()
    meta = service.spreadsheets().get(spreadsheetId=ROSTER_SHEET_ID).execute()
    tab_title = pick_today_tab_title(meta)

    # Column B = names, Column F = times (adjust range if needed)
    range_ = f"{tab_title}!B2:F"
    resp = service.spreadsheets().values().get(
        spreadsheetId=ROSTER_SHEET_ID,
        range=range_
    ).execute()

    values = resp.get("values", [])
    roster = []
    for row in values:
        # row[0] = Column B (name), row[4] = Column F (time) if present
        name = row[0].strip() if len(row) > 0 and row[0].strip() else None
        time_str = row[4].strip() if len(row) > 4 and row[4].strip() else None
        if not name:
            continue
        roster.append({"name": name, "time": time_str})

    return roster


if __name__ == "__main__":
    print(get_today_roster())
