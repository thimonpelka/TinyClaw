from pathlib import Path

from auth import token_store

_TTL_CHOICES = {"1": "never", "2": "30d", "3": "forever"}
_TTL_LABELS = {"never": "this session only", "30d": "30 days", "forever": "forever"}


def resolve_credentials(
    service_name: str,
    env_template: dict[str, str],
    store_path: Path = token_store.STORE_PATH,
) -> dict[str, str]:
    """
    Return env vars for a service.
    Uses stored credentials if valid; otherwise prompts the user on the CLI.

    env_template: the `env` dict from mcp.json (keys are env var names,
                  values are human-readable hints shown in the prompt).
    """
    if not env_template:
        return {}

    stored = token_store.get_credentials(service_name, store_path)
    if stored:
        return stored

    print(f"\n[TinyClaw] '{service_name}' needs credentials.")
    env_vars: dict[str, str] = {}
    for key, hint in env_template.items():
        value = input(f"  {key} (hint: {hint}): ").strip()
        env_vars[key] = value

    ttl = _prompt_ttl()
    token_store.store_credentials(service_name, env_vars, ttl, store_path)
    return env_vars


def _prompt_ttl() -> str:
    print("  Save credentials for: (1) This session only  (2) 30 days  (3) Forever")
    while True:
        choice = input("  Choice [1/2/3]: ").strip()
        if choice in _TTL_CHOICES:
            ttl = _TTL_CHOICES[choice]
            print(f"  Saved for: {_TTL_LABELS[ttl]}")
            return ttl
        print("  Please enter 1, 2, or 3.")
