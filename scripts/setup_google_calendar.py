"""
One-time Google Calendar authorization.
Run this once before using the google_calendar plugin:

    uv run python setup_google_calendar.py

Opens a browser for Google sign-in, then saves token.json to the project root.
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")

if not CREDS_FILE.exists():
    print("Error: credentials.json not found in the project root.")
    print("Download it from Google Cloud Console:")
    print("  APIs & Services → Credentials → OAuth 2.0 Client ID → Download JSON")
    raise SystemExit(1)

flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
creds = flow.run_local_server(port=0)
TOKEN_FILE.write_text(creds.to_json())
print(f"Authorization complete. {TOKEN_FILE} saved.")
print("You can now use the google_calendar plugin in TinyClaw.")
