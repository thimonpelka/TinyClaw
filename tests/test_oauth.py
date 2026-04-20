import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from auth.oauth import resolve_credentials


def test_returns_stored_credentials_when_valid(tmp_path):
    store_path = tmp_path / "tokens.json"
    future = (datetime.now() + timedelta(days=1)).isoformat()
    store_path.write_text(json.dumps({
        "discord": {"DISCORD_TOKEN": "stored-token", "expires_at": future}
    }))

    result = resolve_credentials(
        "discord", {"DISCORD_TOKEN": "placeholder"}, store_path=store_path
    )
    assert result == {"DISCORD_TOKEN": "stored-token"}


def test_prompts_and_stores_forever_when_no_credentials(tmp_path):
    store_path = tmp_path / "tokens.json"

    # input() calls: one for DISCORD_TOKEN value, one for TTL choice ("3" = forever)
    with patch("builtins.input", side_effect=["my-secret-token", "3"]):
        result = resolve_credentials(
            "discord", {"DISCORD_TOKEN": "your-discord-bot-token"}, store_path=store_path
        )

    assert result == {"DISCORD_TOKEN": "my-secret-token"}
    data = json.loads(store_path.read_text())
    assert data["discord"]["DISCORD_TOKEN"] == "my-secret-token"
    assert data["discord"]["expires_at"] is None


def test_prompts_and_does_not_persist_for_never(tmp_path):
    store_path = tmp_path / "tokens.json"

    with patch("builtins.input", side_effect=["my-secret-token", "1"]):
        result = resolve_credentials(
            "discord", {"DISCORD_TOKEN": "your-discord-bot-token"}, store_path=store_path
        )

    assert result == {"DISCORD_TOKEN": "my-secret-token"}
    assert not store_path.exists()


def test_empty_env_template_returns_empty_without_prompting(tmp_path):
    store_path = tmp_path / "tokens.json"

    with patch("builtins.input", side_effect=Exception("should not be called")):
        result = resolve_credentials("no-auth-service", {}, store_path=store_path)

    assert result == {}


def test_invalid_ttl_choice_reprompts(tmp_path):
    store_path = tmp_path / "tokens.json"

    # First TTL answer is invalid ("9"), second is valid ("2" = 30d)
    with patch("builtins.input", side_effect=["my-token", "9", "2"]):
        result = resolve_credentials(
            "svc", {"API_KEY": "hint"}, store_path=store_path
        )

    assert result == {"API_KEY": "my-token"}
    data = json.loads(store_path.read_text())
    assert data["svc"]["expires_at"] is not None  # 30d, not None
