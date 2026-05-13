import os
import json
import datetime as dt
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load service account JSON from environment (Railway + GitHub Actions)
sa_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)

# Your roster sheet ID
ROSTER_SHEET_ID = os.environ.get("ROSTER_SHEET_ID")

def pick_today_tab_title(sheet_metadata: dict) -> str:
    """Fuzzy match today's tab, e.g. 'May 13 2026'."""
    today = dt.date.today()
    month_name = today.strftime("%B")      # May
    month_short = today.strftime("%b")     # May
    day = str(today.day)                   # 13
    year = str(today.year)                 # 2026
    iso = today.strftime("%Y-%m-%d")       # 2026-05-13

    candidates = []
    for s in sheet_metadata["sheets"]:
        title = s["properties"]["title"].strip()

        if title == iso:
            return title

        if month_name in title and day in title:
            candidates.append(title)
        if month_short in title and day in title:
            candidates.append(title)
        if day in title and month_name in title:
            candidates.append(title)
        if day in title and month_short in title:
            candidates.append(title)
        if year in title and (month_name in title or month_short in title):
            candidates.append(title)

    if candidates:
        return sorted(candidates, key=len, reverse=True)[0]

    return sheet_metadata["sheets"][0]["properties"]["title"]


def get_today_roster():
    """Returns list of {'name': ..., 'time': ...} from today's tab."""
    service = build("sheets", "v4", credentials=creds)

    meta = service.spreadsheets().get(spreadsheetId=ROSTER_SHEET_ID).execute()
    tab_title = pick_today_tab_title(meta)

    range_ = f"{tab_title}!B2:F"
    resp = service.spreadsheets().values().get(
        spreadsheetId=ROSTER_SHEET_ID,
        range=range_
    ).execute()

    values = resp.get("values", [])
    roster = []

    for row in values:
        name = row[0].strip() if len(row) > 0 and row[0].strip() else None
        time_str = row[4].strip() if len(row) > 4 and row[4].strip() else None
        if not name:
            continue
        roster.append({"name": name, "time": time_str})

    return roster


if __name__ == "__main__":
    print(get_today_roster())
