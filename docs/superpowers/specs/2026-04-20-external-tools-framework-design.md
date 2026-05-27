# External Tools Framework Design

**Date:** 2026-04-20
**Status:** Approved

## Goal

Add a general-purpose framework that lets TinyClaw connect to external services (Gmail, Google Calendar, Discord, WhatsApp, etc.) via community MCP servers, configured with a standard `mcp.json` file. Authentication is handled interactively with configurable token persistence. Custom services can still be written as Python plugins.

---

## Architecture

Five components, everything else unchanged:

```
mcp.json               ← user-editable service registry (standard MCP format)
auth/oauth.py          ← credential prompting + TTL selection
auth/token_store.py    ← ~/.tinyclaw/tokens.json with expiry metadata
main.py  (extended)    ← connects to N MCP servers, aggregates + routes tools
plugins/*.py           ← unchanged custom plugin system
```

At startup, `main.py` reads `mcp.json`, checks the token store for each service, prompts auth for any missing/expired credentials, then opens a `ClientSession` per service. All tools from all sessions are merged into one flat list for the LLM. A `tool_registry: dict[str, ClientSession]` maps each tool name to its session for routing.

---

## Configuration: `mcp.json`

Uses the de facto standard MCP config format (same as Claude Desktop / Cursor) so community server README snippets can be copy-pasted directly. TinyClaw-specific settings live in a separate `tinyclaw` block.

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
    "discord": {
      "command": "uvx",
      "args": ["mcp-server-discord"],
      "env": {
        "DISCORD_TOKEN": "your-token-here"
      }
    }
  },
  "tinyclaw": {
    "token_ttl": {
      "gmail": "30d",
      "discord": "forever"
    }
  }
}
```

`token_ttl` options: `"never"` (session only), `"30d"` (30 days), `"forever"`.

The local `mcp_server.py` + `plugins/` is always loaded and does not appear in `mcp.json`.

---

## Auth & Token Flow

Community MCP servers handle their own OAuth browser flow internally. TinyClaw's role is credential storage and injection.

**First-time setup (OAuth services):**
1. TinyClaw detects missing or expired credentials for a service
2. TUI prompt: *"Gmail needs credentials. Press Enter to set up..."*
3. TinyClaw spawns the MCP server process; the server itself opens the browser for the OAuth flow
4. User completes login in the browser; the server writes its own credential file
5. TinyClaw asks: *"Save credentials for: (1) This session, (2) 30 days, (3) Forever"*
6. Credentials (the path/value from `env`) stored in `~/.tinyclaw/tokens.json` with expiry timestamp

**First-time setup (API key services):**
1. TinyClaw detects missing or expired credentials
2. TUI shows an input field: *"Enter your Discord token:"*
3. User pastes the key; TinyClaw asks for TTL (same three options)
4. Key stored in `~/.tinyclaw/tokens.json`; injected as env var when spawning the server

**Subsequent startups:**
- Valid credentials are loaded from the token store and injected into the server process `env` automatically — no prompt shown

**Token store format (`~/.tinyclaw/tokens.json`):**
```json
{
  "gmail": {
    "GMAIL_CREDENTIALS_FILE": "~/.tinyclaw/gmail_creds.json",
    "expires_at": "2026-05-20T00:00:00"
  },
  "discord": {
    "DISCORD_TOKEN": "abc123",
    "expires_at": null
  }
}
```

`expires_at: null` means stored forever. Session-only credentials are never written to disk.

---

## Tool Aggregation & Routing

`main.py:run()` is extended to connect to all configured services:

```python
sessions: dict[str, ClientSession] = {}
tool_registry: dict[str, ClientSession] = {}

for name, service in config["mcpServers"].items():
    session = await connect(name, service, token_store)
    sessions[name] = session
    for tool in await session.list_tools():
        tool_registry[tool.name] = session
```

The local `mcp_server.py` is connected first and treated identically to external servers.

`_execute_tool` looks up the right session by tool name:

```python
session = self.tool_registry[name]
result = await session.call_tool(name, args)
```

**Name collisions:** if two servers expose the same tool name, the second one wins and a warning is logged. This is rare since community servers use service-prefixed names (e.g. `gmail_send_email`).

---

## Custom Plugins

The existing `plugins/*.py` pattern is unchanged. For services without a community MCP server, write a Python file in `plugins/`, register tools with `@mcp.tool()`, and they are auto-loaded by `mcp_server.py`. No `mcp.json` entry needed.

---

## File Structure After Implementation

```
mcp.json                         ← new: service registry
auth/
  oauth.py                       ← new: credential prompting + TTL selection
  token_store.py                 ← new: ~/.tinyclaw/tokens.json management
main.py                          ← modified: multi-server connect + routing
mcp_server.py                    ← unchanged
plugins/                         ← unchanged
custom_types.py                  ← unchanged (minor additions for config types)
```

---

## Out of Scope

- A GUI settings screen for managing services (config is edited directly in `mcp.json`)
- Automatic discovery of available community MCP servers
- Dependency-aware tool execution ordering (existing limitation, tracked separately)
