import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

STORE_PATH = Path.home() / ".tinyclaw" / "tokens.json"


def _load(store_path: Path) -> dict:
    if not store_path.exists():
        return {}
    with open(store_path) as f:
        return json.load(f)


def _save(data: dict, store_path: Path) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with open(store_path, "w") as f:
        json.dump(data, f, indent=2)


def get_credentials(
    service_name: str, store_path: Path = STORE_PATH
) -> Optional[dict[str, str]]:
    """Return stored env vars for service if present and not expired, else None."""
    data = _load(store_path)
    entry = data.get(service_name)
    if not entry:
        return None
    expires_at = entry.get("expires_at")
    if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
        return None
    return {k: v for k, v in entry.items() if k != "expires_at"}


def store_credentials(
    service_name: str,
    env_vars: dict[str, str],
    ttl: str,
    store_path: Path = STORE_PATH,
) -> None:
    """
    Persist credentials with the given TTL.
    ttl: "never" (not persisted, session only) | "30d" | "forever"
    """
    if ttl == "never":
        return
    data = _load(store_path)
    expires_at: Optional[str] = None
    if ttl == "30d":
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    data[service_name] = {**env_vars, "expires_at": expires_at}
    _save(data, store_path)
