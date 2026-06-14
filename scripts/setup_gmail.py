"""
One-time Gmail authorization.
Run this once before using the gmail plugin:

    uv run python scripts/setup_gmail.py

Opens a browser for Google sign-in, then saves token_gmail.json to the project root.
You can reuse the same credentials.json from the Google Calendar setup — no new
download needed if you already have it.
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://mail.google.com/"]
CREDS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token_gmail.json")

if not CREDS_FILE.exists():
    print("Error: credentials.json not found in the project root.")
    print("Download it from Google Cloud Console:")
    print("  APIs & Services → Credentials → OAuth 2.0 Client ID → Download JSON")
    print("You can reuse the same file from the Google Calendar setup.")
    raise SystemExit(1)

flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
creds = flow.run_local_server(port=0)
TOKEN_FILE.write_text(creds.to_json())
print(f"Authorization complete. {TOKEN_FILE} saved.")
print("You can now use the gmail plugin in TinyClaw.")
