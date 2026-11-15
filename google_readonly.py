"""Read-only access to Google Calendar and Gmail, for one or more accounts.

Each connected account has its own token in secrets/: token.json for the
first one, token_<name>.json for others (created by auth_google.py <name>).

Safeguards (the assistant can only look, never change anything):
1. OAuth scopes are read-only. Google itself rejects any write, delete or
   send request made with these tokens, whatever the code tries to do.
2. load_credentials() refuses any token that carries another scope.
3. This module only ever calls list/get endpoints.
4. The model that writes the summaries has no tools: it only receives text.
"""
import base64
import glob
import os
import re
from datetime import datetime
from functools import lru_cache
from html import unescape

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

SECRETS_DIR = os.environ.get("GOOGLE_SECRETS_DIR", "secrets")
CLIENT_SECRET_PATH = os.path.join(SECRETS_DIR, "credentials.json")


def token_path(name: str | None = None) -> str:
    return os.path.join(SECRETS_DIR, f"token_{name}.json" if name else "token.json")


def token_paths() -> list[str]:
    """Every connected account's token: token.json first, then token_*.json."""
    paths = sorted(glob.glob(os.path.join(SECRETS_DIR, "token*.json")))
    if not paths:
        raise RuntimeError("Nenhuma conta Google conectada. Rode no Mac: python3 auth_google.py")
    return paths


def load_credentials(path: str) -> Credentials:
    creds = Credentials.from_authorized_user_file(path)
    granted = set(creds.scopes or [])
    if not granted or granted - set(SCOPES):
        raise RuntimeError(
            f"{os.path.basename(path)} tem permissões além de somente-leitura ({sorted(granted)}). "
            "Por segurança o assistente não vai usá-lo. Apague o arquivo e rode auth_google.py de novo."
        )
    if not creds.valid:
        # Refreshed in memory only; the secrets folder is mounted read-only.
        creds.refresh(Request())
    return creds


def _services(path: str):
    creds = load_credentials(path)
    calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return calendar, gmail


@lru_cache(maxsize=None)
def account_email(path: str) -> str:
    """The account's address, used as its label in the briefings."""
    _, gmail = _services(path)
    return gmail.users().getProfile(userId="me").execute()["emailAddress"]


def get_events(start: datetime, end: datetime) -> tuple[list[dict], list[str]]:
    """Primary-calendar events of every connected account between start and end.

    Returns (events, errors): an account that fails is reported in errors
    instead of hiding the other accounts' events.
    """
    events, seen, errors = [], set(), []
    for path in token_paths():
        try:
            calendar, _ = _services(path)
            page = calendar.events().list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=100,
            ).execute()
            label = account_email(path)
        except Exception as e:
            errors.append(f"{os.path.basename(path)}: {e}")
            continue
        for e in page.get("items", []):
            if e.get("status") == "cancelled":
                continue
            s, f = e.get("start", {}), e.get("end", {})
            event = {
                "title": e.get("summary", "(sem título)"),
                "start": s.get("dateTime") or s.get("date"),
                "end": f.get("dateTime") or f.get("date"),
                "all_day": "date" in s,
                "location": e.get("location", ""),
                "account": label,
            }
            # The same meeting can be on both calendars: show it once.
            key = (event["title"], event["start"])
            if key not in seen:
                seen.add(key)
                events.append(event)
    events.sort(key=lambda e: e["start"])
    return events, errors


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


def get_emails(path: str, since: datetime, max_results: int = 40, body_chars: int = 500) -> list[dict]:
    """One account's inbox emails since `since`. Promotions and social are skipped by default."""
    _, gmail = _services(path)
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
