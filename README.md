# TinyClaw

A terminal-based AI chat application that connects a local [Ollama](https://ollama.com) LLM to tools via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). Built with [Textual](https://textual.textualize.io).

```
████████╗██╗███╗   ██╗██╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
╚══██╔══╝██║████╗  ██║╚██╗ ██╔╝██╔════╝██║     ██╔══██╗██║    ██║
   ██║   ██║██╔██╗ ██║ ╚████╔╝ ██║     ██║     ███████║██║ █╗ ██║
   ██║   ██║██║╚██╗██║  ╚██╔╝  ██║     ██║     ██╔══██║██║███╗██║
   ██║   ██║██║ ╚████║   ██║   ╚██████╗███████╗██║  ██║╚███╔███╔╝
   ╚═╝   ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
```

## Features

- **Local LLM via Ollama** — no cloud, no API keys, runs entirely on your machine
- **MCP tool integration** — agentic loop with parallel tool execution
- **Plugin system** — add new tools by dropping a `.py` file into `plugins/`
- **Skills system** — define reusable behavioral guidance in `.md` files
- **Vim-inspired UI** — modal keyboard navigation (Normal / Insert / Tools)
- **Auto-manages Ollama** — starts and stops `ollama serve` automatically if not running
- **Auto-pulls models** — downloads the selected model on first run if not installed

## Quick Start

**1. Install prerequisites**

- [Ollama](https://ollama.com/download) — install and make sure the `ollama` command is available in your terminal
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager used to run the app

**2. Clone and install dependencies**

```bash
git clone <repo-url>
cd TinyClaw
uv sync
```

**3. Run**

```bash
uv run main.py
```

That's it. On first run, TinyClaw will start the Ollama server (if not already running) and automatically download the default model (`qwen2.5:7b`). Once ready, press `i` to enter Insert mode and start chatting.

## Usage

```bash
# Start with the default model (qwen2.5:7b)
uv run main.py

# Start with a specific Ollama model
uv run main.py -m llama3.2

# Start with debug output (shows full agent messages and tool results)
uv run main.py -d
```

## Default Model

TinyClaw defaults to **`qwen2.5:7b`**. Any model available in Ollama can be used — if it isn't installed locally, the app will pull it automatically on startup.

To use a different model permanently, change the `model` class attribute in `main.py`:

```python
model = "llama3.2"
```

Or pass it at runtime with `-m`:

```bash
uv run main.py -m mistral
```

## Keyboard Shortcuts

TinyClaw uses vim-inspired modal navigation:

| Key | Action |
|-----|--------|
| `i` | Enter **Insert** mode (enables text input) |
| `Escape` | Return to **Normal** mode |
| `t` | Show **Tools** panel (lists loaded MCP tools) |
| `c` | Clear chat history |
| `u` | Scroll up |
| `d` | Scroll down |
| `q` | Quit |

## Slash Commands

While in Insert mode, type a `/` command and press Enter:

| Command | Action |
|---------|--------|
| `/skills` | List all available skills |
| `/<skill-name>` | Load a skill — its content will be prepended to your next message |

## Plugin System

Tools are defined as Python files in the `plugins/` directory. Each file is auto-loaded at startup and registers tools with the MCP server using the `@mcp.tool()` decorator.

**Built-in plugins:**

| Plugin | Tools |
|--------|-------|
| `calculator.py` | `calculate` — evaluates math expressions |
| `time.py` | `get_time`, `get_year`, `get_month`, `get_day`, `get_hour` |
| `web_fetch.py` | `fetch_url` — retrieves content from a URL |
| `skills.py` | `use_skill` — loads a skill's guidance content |

**Adding a new tool:**

Create `plugins/mytool.py`:

```python
@mcp.tool()
def my_tool(input: str) -> str:
    """Description of what this tool does."""
    return f"Result: {input}"
```

No imports or registration needed — `mcp` is injected automatically.

## Skills System

Skills are Markdown files in the `skills/` directory that provide the agent with specialized behavioral guidance.

**Skill file format** (`skills/my-skill.md`):

```markdown
---
name: my-skill
description: Short description shown to the agent in the system prompt
when_to_use: Describe the situations where this skill is relevant
---

# My Skill

Full guidance content that the agent reads when the skill is invoked...
```

**How skills work:**

1. At startup, all skills in `skills/` are scanned and their `name`, `description`, and `when_to_use` fields are injected into the system prompt
2. The agent can autonomously call `use_skill("<name>")` to load a skill's full content
3. Users can manually activate a skill with `/skill-name` — the content is then prepended to their next message

## Project Structure

```
TinyClaw/
├── main.py          # Textual app, agentic loop, slash commands
├── mcp_server.py    # FastMCP server + plugin loader
├── custom_types.py  # TypedDicts: OllamaTool, CommandHistory, Skill, Mode
├── app.css          # Textual CSS layout
├── plugins/         # MCP tool plugins (one file per tool set)
└── skills/          # Agent skill definitions (.md files)
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `textual` | Terminal UI framework |
| `ollama` | Ollama Python client |
| `mcp` | Model Context Protocol client/server |
| `anthropic` | Anthropic SDK |
| `httpx` | HTTP client (Ollama health checks) |
