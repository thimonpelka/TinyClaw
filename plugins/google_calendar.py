"""
Plugin: google_calendar
List, create, and delete Google Calendar events.

Setup (one-time):
  1. Go to console.cloud.google.com → Enable the Google Calendar API
  2. APIs & Services → Credentials → Create → OAuth 2.0 Client ID (Desktop app)
  3. Download the JSON → save as credentials.json in the project root
  4. Run: uv run python scripts/setup_google_calendar.py
     This opens a browser for authorization and saves token.json

Optional .env variable:
  CALENDAR_TIMEZONE  — timezone for new events, e.g. "Europe/Berlin" (default: "UTC")
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

_ROOT = Path(__file__).parent.parent
_CREDS_FILE = _ROOT / "credentials.json"
_TOKEN_FILE = _ROOT / "token.json"
_SCOPES = ["https://www.googleapis.com/auth/calendar"]
_TZ = os.environ.get("CALENDAR_TIMEZONE", "UTC")


def _service():
    if not _CREDS_FILE.exists():
        raise RuntimeError(
            "credentials.json not found in the project root. "
            "Download it from Google Cloud Console (APIs & Services → Credentials "
            "→ OAuth 2.0 Client → Download JSON) and run: uv run python scripts/setup_google_calendar.py"
        )
    if not _TOKEN_FILE.exists():
        raise RuntimeError(
            "Not authorized yet. Run: uv run python scripts/setup_google_calendar.py"
        )

    creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), _SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                _TOKEN_FILE.write_text(creds.to_json())
            except RefreshError:
                raise RuntimeError(
                    "Token expired and could not be refreshed. "
                    "Re-run: uv run python scripts/setup_google_calendar.py"
                )
        else:
            raise RuntimeError(
                "Credentials are invalid. Re-run: uv run python scripts/setup_google_calendar.py"
            )

    return build("calendar", "v3", credentials=creds)


@mcp.tool()
def calendar_list_events(
    days_ahead: int = 7,
    max_results: int = 15,
    calendar_id: str = "primary",
) -> str:
    """List upcoming calendar events from now until `days_ahead` days from today."""
    try:
        svc = _service()
        now = datetime.now(timezone.utc)
        until = now + timedelta(days=days_ahead)

        result = (
            svc.events()
            .list(
                calendarId=calendar_id,
                timeMin=now.isoformat(),
                timeMax=until.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        items = result.get("items", [])
        if not items:
            return f"No events in the next {days_ahead} day(s)."

        lines = []
        for event in items:
            start = event["start"].get("dateTime") or event["start"].get("date", "?")
            title = event.get("summary", "(no title)")
            eid = event["id"]
            desc = event.get("description", "")
            line = f"[{eid}] {start}  {title}"
            if desc:
                line += f"\n    {desc.splitlines()[0]}"
            lines.append(line)

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def calendar_create_event(
    title: str,
    start: str,
    end: str,
    description: str = "",
    calendar_id: str = "primary",
) -> str:
    """
    Create a new calendar event.
    start / end: ISO 8601 datetime strings — e.g. "2024-06-15T14:00:00".
    Timezone is taken from CALENDAR_TIMEZONE in .env (default: UTC).
    """
    try:
        svc = _service()
        body: dict = {
            "summary": title,
            "start": {"dateTime": start, "timeZone": _TZ},
            "end": {"dateTime": end, "timeZone": _TZ},
        }
        if description:
            body["description"] = description

        event = svc.events().insert(calendarId=calendar_id, body=body).execute()
        return f"Created '{title}' (id: {event['id']})"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def calendar_delete_event(event_id: str, calendar_id: str = "primary") -> str:
    """Delete a calendar event by its ID. Use calendar_list_events to find event IDs."""
    try:
        _service().events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return f"Deleted event {event_id}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def calendar_list_calendars() -> str:
    """List all Google Calendars available to this account, with their IDs."""
    try:
        result = _service().calendarList().list().execute()
        items = result.get("items", [])
        if not items:
            return "No calendars found."
        return "\n".join(f"[{c['id']}] {c['summary']}" for c in items)
    except Exception as e:
        return f"Error: {e}"
