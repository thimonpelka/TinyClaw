# TinyClaw

You can use a local LLM - install ollama qwen3.5:4b

Or use a free hosted LLM - from https://openrouter.ai
Do this by 1st creating an account. 2nd click 'Get API Key'. 3rd set Credit limit to 0. copy API Key. create .env in same dir as main and add API Keys as displayed in .env.example

Either way update PROVIDER and MODEL in config.py (choose a currently free model from https://openrouter.ai if this option is used)


Start TinyClaw by

uv run main.py

# Use a different Ollama model
uv run main.py -m llama3.2

# Show debug output (agent messages, tool results)
uv run main.py -d
```

Any model available in Ollama works. If the model isn't installed locally, TinyClaw pulls it automatically on startup.

## Keyboard Shortcuts

TinyClaw uses vim-inspired modal navigation. Most shortcuts work in Normal mode (the default). Press `i` to type a message.

| Key | Mode | Action |
|-----|------|--------|
| `i` | Normal | Enter **Insert** mode — enables the text input |
| `Escape` | Insert | Return to **Normal** mode |
| `t` | Normal | Show loaded MCP tools and their descriptions |
| `s` | Normal | Browse available skills |
| `c` | Normal | Clear the chat history |
| `u` | Normal | Scroll up |
| `d` | Normal | Scroll down |
| `q` | Normal | Quit |

## Slash Commands

Type a `/` command in the input box and press Enter. Commands are available in Insert mode.

| Command | Description |
|---------|-------------|
| `/skills` | List all available skills and their active state |
| `/<skill-name>` | Activate a skill — it will be prepended to all future messages |
| `/<skill-name> <message>` | Use a skill for this one message only (inline, one-shot) |
| `/disable-skills` | Deactivate all active skills |
| `/disable-skills <name>` | Deactivate a specific skill by name |

Active skills are shown as colored badges in the status bar directly below the input box. Each skill always gets the same color across restarts.

## Skills

Skills are Markdown files in the `skill-definitions/` directory. They give the agent specialized behavioral instructions for particular tasks — for example, always responding in a certain style, following a structured format, or focusing on a specific domain.

**Example skill** (`skill-definitions/my-skill.md`):

```markdown
---
name: my-skill
description: Short description shown to the agent
when_to_use: When the user asks about X
---

# My Skill

When this skill is active, always respond in bullet points and keep answers under 100 words.
```

**To add a new skill:** create a `.md` file in `skill-definitions/` with the frontmatter above, then restart the app. No code changes needed.

See [`features/skill-definitions/README.md`](features/skill-definitions/README.md) for full documentation on the skills system, including the file format, how skills are injected, and the `SkillsManager` API.

See [`features/commands/README.md`](features/commands/README.md) for documentation on slash commands, the command registry, and how to add new commands.

## Plugins (MCP Tools)

Tools are Python files in the `plugins/` directory. Each file is auto-loaded at startup and registers its tools with the MCP server using the `@mcp.tool()` decorator — no imports or registration boilerplate needed.

**Built-in plugins:**

| Plugin | Tools provided |
|--------|---------------|
| `calculator.py` | `calculate` — evaluates math expressions |
| `time.py` | `get_time`, `get_year`, `get_month`, `get_day`, `get_hour` |
| `web_fetch.py` | `fetch_url` — retrieves content from a URL |
| `skills.py` | `use_skill` — loads a skill's full guidance (used by the agent autonomously) |

**Adding a new tool** — create `plugins/mytool.py`:

```python
@mcp.tool()
def my_tool(input: str) -> str:
    """Description of what this tool does."""
    return f"Result: {input}"
```

Restart the app and the tool is available to the agent.

## Project Structure

```
TinyClaw/
├── main.py              # Textual app, agentic loop, startup
├── mcp_server.py        # FastMCP server + plugin loader
├── custom_types.py      # Shared TypedDicts and enums
├── app.css              # Textual CSS layout
├── plugins/             # MCP tool plugins (one .py file per tool set)
├── skill-definitions/              # Agent skill definitions (.md files)
└── features/
    ├── skill-definitions/          # Skills state, loading, prompting (see README inside)
    └── commands/        # Slash-command registry and handlers (see README inside)
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `textual` | Terminal UI framework |
| `ollama` | Ollama Python client |
| `mcp` | Model Context Protocol client/server |
| `httpx` | HTTP client (Ollama health checks) |
