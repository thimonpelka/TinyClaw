import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from auth.token_store import get_credentials, store_credentials


def test_get_credentials_missing_service(tmp_path):
    assert get_credentials("gmail", tmp_path / "tokens.json") is None


def test_get_credentials_expired(tmp_path):
    store_path = tmp_path / "tokens.json"
    past = (datetime.now() - timedelta(days=1)).isoformat()
    store_path.write_text(json.dumps({"gmail": {"TOKEN": "abc", "expires_at": past}}))
    assert get_credentials("gmail", store_path) is None


def test_get_credentials_valid_with_expiry(tmp_path):
    store_path = tmp_path / "tokens.json"
    future = (datetime.now() + timedelta(days=1)).isoformat()
    store_path.write_text(json.dumps({"gmail": {"TOKEN": "abc", "expires_at": future}}))
    assert get_credentials("gmail", store_path) == {"TOKEN": "abc"}


def test_get_credentials_forever(tmp_path):
    store_path = tmp_path / "tokens.json"
    store_path.write_text(json.dumps({"discord": {"DISCORD_TOKEN": "xyz", "expires_at": None}}))
    assert get_credentials("discord", store_path) == {"DISCORD_TOKEN": "xyz"}


def test_store_never_does_not_write(tmp_path):
    store_path = tmp_path / "tokens.json"
    store_credentials("gmail", {"TOKEN": "abc"}, "never", store_path)
    assert not store_path.exists()


def test_store_30d_writes_with_future_expiry(tmp_path):
    store_path = tmp_path / "tokens.json"
    store_credentials("gmail", {"TOKEN": "abc"}, "30d", store_path)
    data = json.loads(store_path.read_text())
    assert data["gmail"]["TOKEN"] == "abc"
    expires = datetime.fromisoformat(data["gmail"]["expires_at"])
    assert expires > datetime.now() + timedelta(days=29)


def test_store_forever_writes_null_expiry(tmp_path):
    store_path = tmp_path / "tokens.json"
    store_credentials("discord", {"DISCORD_TOKEN": "xyz"}, "forever", store_path)
    data = json.loads(store_path.read_text())
    assert data["discord"]["DISCORD_TOKEN"] == "xyz"
    assert data["discord"]["expires_at"] is None


def test_store_creates_parent_directory(tmp_path):
    store_path = tmp_path / "nested" / "dir" / "tokens.json"
    store_credentials("svc", {"K": "v"}, "forever", store_path)
    assert store_path.exists()
