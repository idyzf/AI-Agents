"""Run on the Mac (not in Docker) to connect a Google account, read-only.

    python3 auth_google.py            # first account  -> secrets/token.json
    python3 auth_google.py trabalho   # another account -> secrets/token_trabalho.json

Opens the browser: log in with the account you want and approve READ-ONLY
access to Calendar and Gmail. Each account needs to be listed as a test user
in the Google Cloud console while the app is in "Testing" mode.
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from google_readonly import CLIENT_SECRET_PATH, SCOPES, account_email, token_path, token_paths

name = sys.argv[1] if len(sys.argv) > 1 else None
path = token_path(name)

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
# prompt=select_account so the browser asks which Google account to use.
creds = flow.run_local_server(port=0, prompt="select_account consent")

if set(creds.scopes or []) - set(SCOPES):
    raise SystemExit("Permissões inesperadas concedidas; token não salvo.")

email = build("gmail", "v1", credentials=creds, cache_discovery=False).users().getProfile(userId="me").execute()["emailAddress"]
try:
    existing = {account_email(p): p for p in token_paths() if p != path}
except RuntimeError:  # no account connected yet
    existing = {}
if email in existing:
    raise SystemExit(f"{email} já está conectado em {existing[email]}. Token não salvo.")
with open(path, "w") as f:
    f.write(creds.to_json())
print(f"Pronto: {email} conectado (somente leitura) em {path}.")
