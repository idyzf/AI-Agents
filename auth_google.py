"""Run once on the Mac (not in Docker) to authorize read-only access.

    python3 auth_google.py

Opens the browser, you log in to Google and approve READ-ONLY access to
Calendar and Gmail. Saves secrets/token.json, which the bot then uses.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

from google_readonly import CLIENT_SECRET_PATH, SCOPES, TOKEN_PATH

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
creds = flow.run_local_server(port=0)

if set(creds.scopes or []) - set(SCOPES):
    raise SystemExit("Permissões inesperadas concedidas; token não salvo.")

with open(TOKEN_PATH, "w") as f:
    f.write(creds.to_json())
print(f"Pronto: {TOKEN_PATH} salvo com acesso somente-leitura.")
