# External Tools Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a general-purpose framework that connects TinyClaw to any number of external MCP servers (Gmail, Discord, etc.) configured via `mcp.json`, with interactive credential prompting and configurable token persistence.

**Architecture:** `main.py` is extended to read `mcp.json` and open one `ClientSession` per configured service using `AsyncExitStack`. A `tool_registry: dict[str, ClientSession]` aggregates all tools from all sessions; `ChatApp._execute_tool` routes each tool call to the correct session. A new `auth/` package handles credential storage (`token_store.py`) and interactive prompting (`oauth.py`).

**Tech Stack:** Python 3.14, `mcp` (FastMCP / ClientSession / StdioServerParameters), `ollama`, `textual`, `contextlib.AsyncExitStack`, `pytest`

---

## File Map

| File | Status | Responsibility |
|------|--------|----------------|
| `auth/__init__.py` | Create | Makes `auth` a package |
| `auth/token_store.py` | Create | Read/write `~/.tinyclaw/tokens.json` with TTL logic |
| `auth/oauth.py` | Create | Resolve credentials: check store, prompt if missing |
| `custom_types.py` | Modify | Add `McpServiceConfig`, `McpConfig` TypedDicts |
| `main.py` | Modify | `load_mcp_config()`, multi-server `run()`, `ChatApp` uses `tool_registry` |
| `mcp.json.example` | Create | Example config users can copy |
| `tests/test_token_store.py` | Create | Unit tests for token_store |
| `tests/test_oauth.py` | Create | Unit tests for credential resolution |
| `tests/test_main_config.py` | Create | Unit tests for `load_mcp_config` |

---

## Task 1: Token Store

**Files:**
- Create: `auth/__init__.py`
- Create: `auth/token_store.py`
- Create: `tests/test_token_store.py`

- [ ] **Step 1: Create the auth package**

Create `auth/__init__.py` with empty content:

```python
```

(Empty file — just makes `auth` importable as a package.)

- [ ] **Step 2: Write failing tests**

Create `tests/test_token_store.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_token_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'auth'`

- [ ] **Step 4: Implement `auth/token_store.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_token_store.py -v
```

Expected: 8 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add auth/__init__.py auth/token_store.py tests/test_token_store.py
git commit -m "feat(): add token store with TTL-based credential persistence"
```

---

## Task 2: Credential Resolution

**Files:**
- Create: `auth/oauth.py`
- Create: `tests/test_oauth.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_oauth.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_oauth.py -v
```

Expected: `ModuleNotFoundError: No module named 'auth.oauth'`

- [ ] **Step 3: Implement `auth/oauth.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_oauth.py -v
```

Expected: 5 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add auth/oauth.py tests/test_oauth.py
git commit -m "feat(): add credential resolution with interactive TTL prompting"
```

---

## Task 3: Config Types

**Files:**
- Modify: `custom_types.py`

- [ ] **Step 1: Add `McpServiceConfig` and `McpConfig` to `custom_types.py`**

Open `custom_types.py`. The current content is:

```python
from typing import TypedDict
from enum import Enum


class FunctionSpec(TypedDict):
    name: str
    description: str
    parameters: dict[str, str]


class OllamaTool(TypedDict):
    type: str
    function: FunctionSpec


class CommandHistory(TypedDict):
    role: str
    content: str


class Mode(str, Enum):
    NORMAL = "normal"
    INSERT = "insert"
    TOOLS = "tools"
```

Replace with:

```python
from typing import Any, TypedDict
from typing import NotRequired
from enum import Enum


class FunctionSpec(TypedDict):
    name: str
    description: str
    parameters: dict[str, str]


class OllamaTool(TypedDict):
    type: str
    function: FunctionSpec


class CommandHistory(TypedDict):
    role: str
    content: str


class Mode(str, Enum):
    NORMAL = "normal"
    INSERT = "insert"
    TOOLS = "tools"


class McpServiceConfig(TypedDict):
    command: str
    args: list[str]
    env: NotRequired[dict[str, str]]


class McpConfig(TypedDict):
    mcpServers: dict[str, McpServiceConfig]
    tinyclaw: NotRequired[dict[str, Any]]
```

- [ ] **Step 2: Verify no import errors**

```bash
uv run python -c "from custom_types import McpServiceConfig, McpConfig; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add custom_types.py
git commit -m "feat(): add McpServiceConfig and McpConfig types"
```

---

## Task 4: Multi-Server Wiring in `main.py`

**Files:**
- Modify: `main.py`
- Create: `tests/test_main_config.py`

- [ ] **Step 1: Write failing tests for `load_mcp_config`**

Create `tests/test_main_config.py`:

```python
import json
from pathlib import Path

from main import load_mcp_config


def test_load_mcp_config_missing_file(tmp_path):
    result = load_mcp_config(tmp_path / "mcp.json")
    assert result == {"mcpServers": {}}


def test_load_mcp_config_parses_servers(tmp_path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text(json.dumps({
        "mcpServers": {
            "discord": {
                "command": "uvx",
                "args": ["mcp-server-discord"],
                "env": {"DISCORD_TOKEN": "placeholder"}
            }
        }
    }))
    result = load_mcp_config(config_path)
    assert "discord" in result["mcpServers"]
    assert result["mcpServers"]["discord"]["command"] == "uvx"
    assert result["mcpServers"]["discord"]["args"] == ["mcp-server-discord"]


def test_load_mcp_config_no_mcpservers_key(tmp_path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text(json.dumps({"tinyclaw": {"token_ttl": {}}}))
    result = load_mcp_config(config_path)
    assert result.get("mcpServers", {}) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_main_config.py -v
```

Expected: `ImportError` — `load_mcp_config` not yet defined in `main.py`

- [ ] **Step 3: Add imports and `load_mcp_config` to `main.py`**

`main.py` already imports `json`, `sys`, `Path`, `asyncio`, `ClientSession`, `StdioServerParameters`, `stdio_client`. Add only these new imports after the existing import block:

```python
import os
from contextlib import AsyncExitStack
from auth.oauth import resolve_credentials
from custom_types import McpConfig
```

Also update the existing `from custom_types import ...` line from:
```python
from custom_types import CommandHistory, OllamaTool, Mode
```
to:
```python
from custom_types import CommandHistory, McpConfig, OllamaTool, Mode
```

Then add this function anywhere before `run()`:

```python
MCP_CONFIG_PATH = Path(__file__).parent / "mcp.json"


def load_mcp_config(config_path: Path = MCP_CONFIG_PATH) -> McpConfig:
    if not config_path.exists():
        return {"mcpServers": {}}
    with open(config_path) as f:
        data = json.load(f)
    if "mcpServers" not in data:
        data["mcpServers"] = {}
    return data
```

- [ ] **Step 4: Run config tests to verify they pass**

```bash
uv run pytest tests/test_main_config.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: Update `ChatApp.__init__` to accept `tool_registry` instead of `session`**

Find this in `main.py` (around line 53):

```python
    def __init__(
        self, session: ClientSession, tools: list[OllamaTool], args: Namespace, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.session = session
        self.tools = tools
        self.history: list[CommandHistory] = []
        self.mode = Mode.NORMAL
        self.debug_active = args.debug  # pyright: ignore[reportAny]

        self.loading = False
        self.spinner_frame = 0
        self.spinner_task = None
```

Replace with:

```python
    def __init__(
        self, tool_registry: dict[str, ClientSession], tools: list[OllamaTool], args: Namespace, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.tool_registry = tool_registry
        self.tools = tools
        self.history: list[CommandHistory] = []
        self.mode = Mode.NORMAL
        self.debug_active = args.debug  # pyright: ignore[reportAny]

        self.loading = False
        self.spinner_frame = 0
        self.spinner_task = None
```

- [ ] **Step 6: Update `_execute_tool` to route via `tool_registry`**

Find this in `main.py` (around line 371):

```python
        try:
            result = await self.session.call_tool(name, args)  # pyright: ignore[reportArgumentType]
```

Replace with:

```python
        session = self.tool_registry.get(name)
        if session is None:
            self.write_system(log, f"{name} → unknown tool, skipping")
            return {"role": "tool", "content": f"Error: unknown tool '{name}'"}

        try:
            result = await session.call_tool(name, args)  # pyright: ignore[reportArgumentType]
```

- [ ] **Step 7: Replace `run()` with multi-server version**

Find the entire `run()` function (around line 396) and replace it:

```python
async def run(args: Namespace) -> None:
    """
    Loads mcp.json, resolves credentials for each service, connects to all MCP
    servers (local + external), aggregates their tools, and starts the TUI.
    """
    config = load_mcp_config()

    async with AsyncExitStack() as stack:
        tool_registry: dict[str, ClientSession] = {}
        all_tools: list[OllamaTool] = []

        def _register_tools(session: ClientSession, tools_response) -> None:
            for t in tools_response.tools:
                if t.name in tool_registry:
                    print(f"[TinyClaw] Warning: tool '{t.name}' already registered, overwriting.")
                tool_registry[t.name] = session
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema,
                    },
                })

        # Always connect to the local plugin server first
        local_params = StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER_SCRIPT)],
        )
        r, w = await stack.enter_async_context(stdio_client(local_params))
        local_session = await stack.enter_async_context(ClientSession(r, w))
        await local_session.initialize()
        _register_tools(local_session, await local_session.list_tools())

        # Connect to each external service from mcp.json
        for name, service in config.get("mcpServers", {}).items():
            env_template = service.get("env", {})
            resolved_env = resolve_credentials(name, env_template)
            merged_env = {**os.environ, **resolved_env}

            ext_params = StdioServerParameters(
                command=service["command"],
                args=service["args"],
                env=merged_env,
            )
            r, w = await stack.enter_async_context(stdio_client(ext_params))
            ext_session = await stack.enter_async_context(ClientSession(r, w))
            await ext_session.initialize()
            _register_tools(ext_session, await ext_session.list_tools())

        app = ChatApp(tool_registry=tool_registry, tools=all_tools, args=args)
        await app.run_async()
```

- [ ] **Step 8: Run the full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASSED (token_store × 8, oauth × 5, main_config × 3)

- [ ] **Step 9: Smoke-test the app with no `mcp.json`**

```bash
uv run main.py
```

Expected: app starts normally, loads only local plugin tools (calculator, time, web_fetch), no errors.

- [ ] **Step 10: Commit**

```bash
git add main.py tests/test_main_config.py
git commit -m "feat(): wire multi-server MCP connections with tool registry routing"
```

---

## Task 5: Example Config

**Files:**
- Create: `mcp.json.example`

- [ ] **Step 1: Create `mcp.json.example`**

```json
{
  "mcpServers": {
    "gmail": {
      "command": "uvx",
      "args": ["mcp-server-gmail"],
      "env": {
        "GMAIL_CREDENTIALS_FILE": "~/.tinyclaw/gmail_creds.json"
      }
    },
    "google-calendar": {
      "command": "uvx",
      "args": ["mcp-server-google-calendar"],
      "env": {
        "GOOGLE_CALENDAR_CREDENTIALS_FILE": "~/.tinyclaw/gcal_creds.json"
      }
    },
    "discord": {
      "command": "uvx",
      "args": ["mcp-server-discord"],
      "env": {
        "DISCORD_TOKEN": "your-discord-bot-token-here"
      }
    }
  },
  "tinyclaw": {
    "token_ttl": {
      "gmail": "30d",
      "google-calendar": "30d",
      "discord": "forever"
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add mcp.json.example
git commit -m "docs(): add mcp.json.example with Gmail, Google Calendar, Discord"
```

---

## Done

After Task 5, the framework is complete. To add a new service:
1. Copy the relevant snippet from the community server's README into `mcp.json`
2. Add a `token_ttl` entry under `tinyclaw`
3. Run `uv run main.py` — TinyClaw will prompt for credentials on first launch

For services without a community MCP server, drop a `.py` file in `plugins/` as before.
