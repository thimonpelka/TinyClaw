"""
Plugin: telegram
Send and receive Telegram messages via a bot.

Required .env variables:
  TELEGRAM_BOT_TOKEN  — bot token from @BotFather
  TELEGRAM_CHAT_ID    — default chat/user ID to send to (optional; can be passed per-call)
"""

import json
import os
import urllib.request


_API = "https://api.telegram.org"


def _token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")
    return token


def _post(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{_API}/bot{_token()}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{_API}/bot{_token()}{path}"
    if params:
        from urllib.parse import urlencode

        url += "?" + urlencode(params)
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read())


@mcp.tool()
def telegram_send(text: str, chat_id: str = "") -> str:
    """Send a Telegram message. Uses TELEGRAM_CHAT_ID from .env if chat_id is not provided."""
    target = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
    if not target:
        return "Error: provide a chat_id or set TELEGRAM_CHAT_ID in .env"

    data = _post("/sendMessage", {"chat_id": target, "text": text})
    if data.get("ok"):
        return f"Sent (message_id: {data['result']['message_id']})"
    return f"Error: {data.get('description', 'unknown error')}"


@mcp.tool()
def telegram_get_updates(limit: int = 10) -> str:
    """Get the most recent messages received by the bot (up to `limit`)."""
    data = _get("/getUpdates", {"limit": limit})
    if not data.get("ok"):
        return f"Error: {data.get('description', 'unknown error')}"

    updates = data.get("result", [])
    if not updates:
        return "No recent messages."

    lines = []
    for update in updates:
        msg = update.get("message") or update.get("channel_post", {})
        if not msg:
            continue
        sender = msg.get("from") or msg.get("chat", {})
        name = " ".join(
            filter(None, [sender.get("first_name"), sender.get("last_name")])
        ) or sender.get("username", "unknown")
        chat_id_val = msg.get("chat", {}).get("id", "?")
        text = msg.get("text", "[no text]")
        lines.append(f"[chat_id={chat_id_val}] {name}: {text}")

    return "\n".join(lines) if lines else "No text messages found."
