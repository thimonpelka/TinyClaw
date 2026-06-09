# TinyClaw

A terminal-based AI chat application built with [Textual](https://textual.textualize.io). Connects an LLM to tools via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). Supports local models via [Ollama](https://ollama.com) and cloud models via [OpenRouter](https://openrouter.ai).

```
████████╗██╗███╗   ██╗██╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
╚══██╔══╝██║████╗  ██║╚██╗ ██╔╝██╔════╝██║     ██╔══██╗██║    ██║
   ██║   ██║██╔██╗ ██║ ╚████╔╝ ██║     ██║     ███████║██║ █╗ ██║
   ██║   ██║██║╚██╗██║  ╚██╔╝  ██║     ██║     ██╔══██║██║███╗██║
   ██║   ██║██║ ╚████║   ██║   ╚██████╗███████╗██║  ██║╚███╔███╔╝
   ╚═╝   ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
```

## Features

- **Multiple LLM providers** — Ollama (local) or OpenRouter (cloud), switchable via `config.toml`
- **MCP tool integration** — agentic loop with parallel tool execution
- **Plugin system** — add new tools by dropping a `.py` file into `plugins/`
- **Skills system** — reusable behavioral guidance injected into the agent via `.md` files
- **Vim-inspired UI** — modal keyboard navigation (Normal / Insert / Tools)
- **Auto-manages Ollama** — starts and stops `ollama serve` automatically if not running
- **Auto-pulls models** — downloads the selected Ollama model on first run if not installed

---

## Quick Start

**1. Install prerequisites**

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- For local models: [Ollama](https://ollama.com/download)

**2. Clone and install dependencies**

```bash
git clone <repo-url>
cd TinyClaw
uv sync
```

**3. Configure your provider**

On first run, TinyClaw creates a `config.toml` with these defaults:

```toml
provider = "ollama"

[ollama]
default_model = "qwen2.5:7b"

[openrouter]
default_model = "openai/gpt-4o-mini"
```

To use OpenRouter instead, set `provider = "openrouter"` and add your API key to a `.env` file:

```bash
OPENROUTER_API_KEY=sk-or-...
```

**4. Run**

```bash
uv run main.py
```

Once the log shows the provider is ready, press `i` to start chatting.

---

## Configuration

### `config.toml`

Controls which provider is active and the default model for each provider. Created automatically on first run if it doesn't exist.

```toml
# "ollama" or "openrouter"
provider = "ollama"

[ollama]
default_model = "qwen2.5:7b"   # any model available in Ollama

[openrouter]
default_model = "openai/gpt-4o-mini"   # any model slug from openrouter.ai/models
```

### `.env`

Stores secrets. Never committed to git.

```bash
OPENROUTER_API_KEY=sk-or-...   # required for the openrouter provider

TELEGRAM_BOT_TOKEN=...          # required for the telegram plugin
TELEGRAM_CHAT_ID=...            # optional default recipient for telegram_send

CALENDAR_TIMEZONE=Europe/Berlin # optional timezone for new calendar events (default: UTC)
```

### CLI flags

The `-m` flag overrides `default_model` from `config.toml` for the current session only.

```bash
uv run main.py                   # uses provider and model from config.toml
uv run main.py -m llama3.2       # override model for this run
uv run main.py -d                # enable debug output (agent steps, tool results)
uv run main.py -m gpt-4o -d     # combine flags
```

---

## Keyboard Shortcuts

TinyClaw uses vim-inspired modal navigation. The default mode is Normal. Press `i` to type.

| Key | Mode | Action |
|-----|------|--------|
| `i` | Normal | Enter **Insert** mode — enables the text input |
| `Escape` | Insert | Return to **Normal** mode |
| `t` | Normal | Show loaded MCP tools and their descriptions |
| `s` | Normal | Browse available skills |
| `c` | Normal | Clear the chat history and log |
| `u` | Normal | Scroll up |
| `d` | Normal | Scroll down |
| `q` | Normal | Quit |

---

## Slash Commands

Type a `/command` in the input and press Enter. Available while in Insert mode.

| Command | Description |
|---------|-------------|
| `/compact` | Summarize the chat history to free up context window space |
| `/compact N` | Summarize the last N messages only |
| `/skills` | List all available skills and their active state |
| `/<skill-name>` | Activate a skill — prepended to all future messages until disabled |
| `/<skill-name> <message>` | Use a skill for this one message only (inline, one-shot) |
| `/disable-skills` | Deactivate all active skills |
| `/disable-skills <name>` | Deactivate a specific skill by name |

Active skills appear as colored badges in the status bar below the input box.

---

## Skills

Skills are Markdown files in `skill-definitions/`. They give the agent focused behavioral instructions — a response style, a structured format, a domain constraint. They are loaded at startup and can be activated per-message or persistently.

**File format** (`skill-definitions/my-skill.md`):

```markdown
---
name: my-skill
description: Short description shown to the agent and in /skills
when_to_use: When the user asks about X
---

# My Skill

When this skill is active, always respond in bullet points and keep answers under 100 words.
```

**To add a skill:** create the `.md` file in `skill-definitions/` and restart the app. No code changes needed.

See [`features/skills/README.md`](features/skills/README.md) for full documentation on the skills system, including how skills are injected into the system prompt and the `SkillsManager` API.

---

## Plugins (MCP Tools)

Tools are Python files in `plugins/`. Each file is auto-loaded at startup and registers its tools via the `@mcp.tool()` decorator. The `mcp` instance is injected automatically — no imports or boilerplate needed.

**Built-in plugins:**

| Plugin | Tools |
|--------|-------|
| `calculator.py` | `calculate` — evaluates math expressions safely |
| `time.py` | `get_time`, `get_year`, `get_month`, `get_day`, `get_hour` |
| `web_fetch.py` | `web_fetch` — retrieves and returns content from a URL |
| `telegram.py` | `telegram_send`, `telegram_get_updates` — send and read Telegram messages via a bot |
| `google_calendar.py` | `calendar_list_events`, `calendar_create_event`, `calendar_delete_event`, `calendar_list_calendars` |
| `skills.py` | `use_skill` — loads a skill's full guidance (used by the agent autonomously) |

**Adding a new tool** — create `plugins/mytool.py`:

```python
@mcp.tool()
def my_tool(input: str) -> str:
    """Description shown to the agent."""
    return f"Result: {input}"
```

Restart and the tool is immediately available to the agent.

See [`features/commands/README.md`](features/commands/README.md) for documentation on slash commands and how to add new ones.

---

## Adding a New LLM Provider

Providers live in `llm/`. To add a new one:

1. Create `llm/myprovider.py` implementing four methods:

```python
from collections.abc import Callable
from .protocol import LLMMessage, ToolCall

class MyProvider:
    async def ensure_ready(
        self, model: str,
        on_log: Callable[[str], None] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        # validate credentials, check connectivity, etc.
        ...

    async def chat(self, messages: list[dict], tools: list[dict], model: str) -> LLMMessage:
        # call your API, return normalized LLMMessage
        ...

    def make_tool_result(self, tool_call: ToolCall, content: str) -> dict:
        # return {"role": "tool", "content": content, ...}
        ...

    def shutdown(self) -> None:
        # cleanup (optional)
        ...
```

2. Register it in `llm/__init__.py`:

```python
from .myprovider import MyProvider

_REGISTRY: dict[str, type] = {
    "ollama": OllamaProvider,
    "openrouter": OpenRouterProvider,
    "myprovider": MyProvider,   # add this
}
```

3. Add a default model block to the generated `config.toml` template in `llm/config.py`.

---

## Project Structure

```
TinyClaw/
├── main.py                  # Textual app, agentic loop, startup
├── mcp_server.py            # FastMCP server + plugin loader
├── custom_types.py          # Shared TypedDicts and enums
├── app.css                  # Textual CSS (Tokyo Night theme)
├── config.toml              # Provider selection and model defaults (auto-created)
├── .env                     # API keys — never committed
│
├── llm/                     # LLM provider abstraction
│   ├── __init__.py          # get_provider(), public API
│   ├── protocol.py          # LLMProvider protocol, LLMMessage, ToolCall
│   ├── config.py            # config.toml loading and model resolution
│   ├── ollama.py            # Ollama provider (local)
│   └── openrouter.py        # OpenRouter provider (cloud)
│
├── plugins/                 # MCP tool definitions (auto-loaded)
├── skill-definitions/       # Agent skill files (.md)
│
└── features/
    ├── commands/            # Slash-command registry and handlers
    └── skills/              # Skills loading, state, and prompt injection
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `textual` | Terminal UI framework |
| `ollama` | Ollama Python client |
| `mcp` | Model Context Protocol client/server |
| `httpx` | HTTP client (Ollama health checks, OpenRouter API calls) |
| `python-dotenv` | Loads `.env` file into the environment |
