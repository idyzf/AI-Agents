"""Read-only access to Google Calendar and Gmail.

Safeguards (the assistant can only look, never change anything):
1. OAuth scopes are read-only. Google itself rejects any write, delete or
   send request made with this token, whatever the code tries to do.
2. load_credentials() refuses to start if the token carries any other scope.
3. This module only ever calls list/get endpoints.
4. The model that writes the summaries has no tools: it only receives text.
"""
import base64
import os
import re
from datetime import datetime
from html import unescape

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

SECRETS_DIR = os.environ.get("GOOGLE_SECRETS_DIR", "secrets")
TOKEN_PATH = os.path.join(SECRETS_DIR, "token.json")
CLIENT_SECRET_PATH = os.path.join(SECRETS_DIR, "credentials.json")


def load_credentials() -> Credentials:
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(
            f"{TOKEN_PATH} não encontrado. Rode no Mac: python3 auth_google.py"
        )
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    granted = set(creds.scopes or [])
    if not granted or granted - set(SCOPES):
        raise RuntimeError(
            f"Token com permissões além de somente-leitura ({sorted(granted)}). "
            "Por segurança o assistente não vai usá-lo. Apague o token e rode auth_google.py de novo."
        )
    if not creds.valid:
        # Refreshed in memory only; the secrets folder is mounted read-only.
        creds.refresh(Request())
    return creds


def _services():
    creds = load_credentials()
    calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return calendar, gmail


def get_events(start: datetime, end: datetime) -> list[dict]:
    """Events from the primary calendar (plus CALENDAR_IDS, comma-separated) between start and end."""
    calendar, _ = _services()
    calendar_ids = ["primary"] + [c for c in os.environ.get("CALENDAR_IDS", "").split(",") if c.strip()]
    events = []
    for cal_id in calendar_ids:
        page = calendar.events().list(
            calendarId=cal_id.strip(),
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=100,
        ).execute()
        for e in page.get("items", []):
            if e.get("status") == "cancelled":
                continue
            s, f = e.get("start", {}), e.get("end", {})
            events.append({
                "title": e.get("summary", "(sem título)"),
                "start": s.get("dateTime") or s.get("date"),
                "end": f.get("dateTime") or f.get("date"),
                "all_day": "date" in s,
                "location": e.get("location", ""),
            })
    events.sort(key=lambda e: e["start"])
    return events


def _header(headers: list, name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _body_text(payload: dict) -> str:
    """Plain text of a message, preferring text/plain over HTML."""
    plain, html = [], []

    def walk(part):
        data = part.get("body", {}).get("data")
        mime = part.get("mimeType", "")
        if data:
            text = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            (plain if mime == "text/plain" else html if mime == "text/html" else []).append(text)
        for p in part.get("parts", []) or []:
            walk(p)

    walk(payload)
    if plain:
        text = "\n".join(plain)
    else:
        text = re.sub(r"<(script|style).*?</\1>", " ", "\n".join(html), flags=re.S | re.I)
        text = unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


def get_emails(since: datetime, max_results: int = 40, body_chars: int = 500) -> list[dict]:
    """Inbox emails received since `since`. Promotions and social are skipped by default."""
    _, gmail = _services()
    query = f"in:inbox after:{int(since.timestamp())}"
    if os.environ.get("INCLUDE_PROMOTIONS", "false").lower() != "true":
        query += " -category:promotions -category:social"
    listed = gmail.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    emails = []
    for ref in listed.get("messages", []):
        msg = gmail.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        headers = msg.get("payload", {}).get("headers", [])
        emails.append({
            "from": _header(headers, "From"),
            "subject": _header(headers, "Subject") or "(sem assunto)",
            "body": _body_text(msg.get("payload", {}))[:body_chars] or msg.get("snippet", ""),
            "unread": "UNREAD" in msg.get("labelIds", []),
        })
    return emails
