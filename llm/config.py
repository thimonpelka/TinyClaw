import tomllib
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.toml"

_DEFAULT_CONFIG = """\
# TinyClaw LLM provider configuration
provider = "ollama"

[ollama]
default_model = "qwen2.5:7b"

[openrouter]
default_model = "openai/gpt-4o-mini"
"""


def load_config(path: Path = _CONFIG_PATH) -> dict:
    if not path.exists():
        path.write_text(_DEFAULT_CONFIG)
    with open(path, "rb") as f:
        return tomllib.load(f)


def resolve_model(config: dict, provider: str, cli_model: str | None) -> str:
    """Return the model to use: CLI flag > config default."""
    if cli_model:
        return cli_model
    model = config.get(provider, {}).get("default_model", "")
    if not model:
        raise ValueError(f"No default_model configured for provider '{provider}' in config.toml")
    return model
