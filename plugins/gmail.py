"""
Plugin: gmail
Read, search, send, and reply to emails via Gmail.

Setup (one-time):
  1. Go to console.cloud.google.com → Enable the Gmail API
  2. APIs & Services → Credentials → Create → OAuth 2.0 Client ID (Desktop app)
     You can reuse the same credentials.json from the Google Calendar setup.
  3. Run: uv run python scripts/setup_gmail.py
     This opens a browser for authorization and saves token_gmail.json

No additional .env variables required.
"""

import base64
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

_ROOT = Path(__file__).parent.parent
_CREDS_FILE = _ROOT / "credentials.json"
_TOKEN_FILE = _ROOT / "token_gmail.json"
_SCOPES = ["https://mail.google.com/"]


def _service():
    if not _CREDS_FILE.exists():
        raise RuntimeError(
            "credentials.json not found in the project root. "
            "Download it from Google Cloud Console (APIs & Services → Credentials "
            "→ OAuth 2.0 Client → Download JSON) and run: uv run python scripts/setup_gmail.py"
        )
    if not _TOKEN_FILE.exists():
        raise RuntimeError(
            "Not authorized yet. Run: uv run python scripts/setup_gmail.py"
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
                    "Re-run: uv run python scripts/setup_gmail.py"
                )
        else:
            raise RuntimeError(
                "Credentials are invalid. Re-run: uv run python scripts/setup_gmail.py"
            )

    return build("gmail", "v1", credentials=creds)


def _header(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _extract_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            result = _extract_body(part)
            if result:
                return result

    return ""


@mcp.tool()
def gmail_list_emails(max_results: int = 10, query: str = "", label: str = "INBOX") -> str:
    """
    List recent emails. label can be INBOX, SENT, UNREAD, SPAM, TRASH, or any Gmail label.
    Use query for Gmail search syntax, e.g. 'is:unread', 'from:boss@company.com', 'subject:invoice'.
    Returns message IDs needed for gmail_get_email and gmail_reply_email.
    """
    try:
        svc = _service()
        params: dict = {"userId": "me", "maxResults": max_results}
        if label:
            params["labelIds"] = [label.upper()]
        if query:
            params["q"] = query

        result = svc.users().messages().list(**params).execute()
        messages = result.get("messages", [])
        if not messages:
            return "No emails found."

        lines = []
        for m in messages:
            msg = svc.users().messages().get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            subject = _header(msg, "Subject") or "(no subject)"
            sender = _header(msg, "From")
            date = _header(msg, "Date")[:16]
            unread = "●" if "UNREAD" in msg.get("labelIds", []) else " "
            lines.append(f"[{m['id']}] {unread} {date}  {sender}  —  {subject}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def gmail_get_email(message_id: str) -> str:
    """Get the full content of an email by its ID. Use gmail_list_emails to find IDs."""
    try:
        svc = _service()
        msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()

        subject = _header(msg, "Subject") or "(no subject)"
        sender = _header(msg, "From")
        to = _header(msg, "To")
        date = _header(msg, "Date")
        body = _extract_body(msg.get("payload", {})) or "(no plain-text body)"

        return f"From: {sender}\nTo: {to}\nDate: {date}\nSubject: {subject}\n\n{body}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def gmail_send_email(to: str, subject: str, body: str, cc: str = "") -> str:
    """Send a new email."""
    try:
        svc = _service()
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        if cc:
            msg["cc"] = cc

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Sent (message_id: {result['id']})"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def gmail_reply_email(message_id: str, body: str) -> str:
    """Reply to an email thread by the original message ID."""
    try:
        svc = _service()
        original = svc.users().messages().get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "Message-ID"],
        ).execute()

        sender = _header(original, "From")
        subject = _header(original, "Subject")
        original_message_id = _header(original, "Message-ID")
        thread_id = original.get("threadId", "")

        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        msg = MIMEText(body)
        msg["to"] = sender
        msg["subject"] = subject
        if original_message_id:
            msg["In-Reply-To"] = original_message_id
            msg["References"] = original_message_id

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = svc.users().messages().send(
            userId="me", body={"raw": raw, "threadId": thread_id}
        ).execute()
        return f"Reply sent (message_id: {result['id']})"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def gmail_mark_read(message_id: str) -> str:
    """Mark an email as read by its ID."""
    try:
        _service().users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return f"Marked as read: {message_id}"
    except Exception as e:
        return f"Error: {e}"
