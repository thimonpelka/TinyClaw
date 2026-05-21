# features/commands

This package handles all slash-command input. It provides a lightweight registry that maps `/command-name` strings to async handler functions, plus the `CommandContext` dataclass that gives handlers access to the UI and skills state without importing from `main.py` or `features/skills` directly.

## Concepts

When a user types a message starting with `/` and presses Enter, `main.py` strips the leading slash and passes the remainder to `CommandRegistry.dispatch()`. The registry either finds an exact-name match or falls back to a registered fallback handler (used for dynamic skill-name routing).

Handlers receive a `CommandContext` — a snapshot of the UI callbacks and skills state they need. They never import from `main.py` or `features/skills` directly; they only depend on `CommandContext` and the `SkillsManagerProtocol` interface.

## Package Structure

```
features/commands/
├── __init__.py               # Public exports + register_all_commands()
├── registry.py               # Command, CommandContext, SkillsManagerProtocol, CommandRegistry
└── handlers/
    ├── __init__.py           # empty
    └── skills_commands.py    # handle_list_skills, handle_disable_skills, handle_skill_by_name
```

## CommandRegistry

The registry stores named commands and one optional fallback. Dispatch is synchronous on name lookup, async on handler invocation.

```python
from features.commands import CommandRegistry, Command, CommandContext, register_all_commands

registry = CommandRegistry()
register_all_commands(registry)

# In an async context:
handled = await registry.dispatch("skills", ctx)   # → True, calls handle_list_skills
handled = await registry.dispatch("unknown", ctx)  # → True, routed to fallback
```

**Methods:**

| Method | Description |
|--------|-------------|
| `register(command)` | Register a named command. Names are matched exactly (case-sensitive). |
| `register_fallback(command)` | Register the fallback handler. Called when no named command matches. Receives the full raw string (e.g. `"my-skill some message"`). |
| `dispatch(raw, ctx)` | Parse `raw`, dispatch to matching command or fallback. Returns `True` if handled, `False` if no handler found. |
| `commands` | Property — returns a copy of the named command dict. |

## CommandContext

`CommandContext` is a `@dataclass` passed to every handler. It carries UI callbacks as callables so handlers can write to the log, show errors, or send messages without depending on `ChatApp` directly.

```python
@dataclass
class CommandContext:
    log: RichLog                                          # Raw RichLog widget
    write_system: Callable[[str], None]                   # Write a dim system message
    write_error: Callable[[str], None]                    # Write a red error message
    send_message: Callable[[str, str], None]              # Send (display_text, full_text) to agent
    update_indicator: Callable[[], None]                  # Refresh the skills status bar
    skills: SkillsManagerProtocol                         # All skills state and operations
    extras: dict[str, Any]                                # Reserved for future expansion
```

`CommandContext` is constructed in `ChatApp.on_input_submitted` using lambdas that close over the active `log` widget:

```python
ctx = CommandContext(
    log=log,
    write_system=lambda t: self.write_system(log, t),
    write_error=lambda t: self.write_error(log, t),
    send_message=lambda display, full: self._send_message(display, full, log),
    update_indicator=self._update_skills_indicator,
    skills=self.skills_manager,
)
```

## SkillsManagerProtocol

`SkillsManagerProtocol` is a `typing.Protocol` defined in `registry.py`. It describes the interface that `CommandContext.skills` must satisfy. This avoids a direct import from `features/skills` into `features/commands`, keeping the two feature modules decoupled.

`SkillsManager` (from `features/skills`) satisfies the protocol by structural subtyping — no explicit `implements` declaration is required.

## Built-in Commands

All built-in commands are registered via `register_all_commands(registry)`:

| Command | Handler | Description |
|---------|---------|-------------|
| `/skills` | `handle_list_skills` | Lists all loaded skills with active state indicators. |
| `/disable-skills [name]` | `handle_disable_skills` | Deactivates a named skill, or all skills if no name given. |
| `/<skill-name>` | `handle_skill_by_name` (fallback) | Activates a skill persistently, or sends an inline one-shot message if text follows the name. |

### `/skills`

Lists every loaded skill. Active skills are marked with `●`.

```
Available skills (● = active):
  [ my-skill ● ] — Short description  (use when: ...)
  [ other-skill ] — Another description  (use when: ...)
```

### `/disable-skills [name]`

```
/disable-skills             # deactivates all active skills
/disable-skills my-skill    # deactivates only "my-skill"
```

Shows an error if the named skill is not currently active.

### `/<skill-name>`

```
/my-skill                       # persistent: skill active for all future messages
/my-skill what is 2 + 2?        # inline: skill applied only to this message
```

**Persistent mode:** activates the skill until explicitly disabled. The skill name appears as a colored badge in the status bar below the input. Shows an error if the skill is already active.

**Inline mode:** the skill content is prepended to the message text before sending. Any currently active persistent skills are also included. The badge is shown in the chat log next to the displayed message. The skill is not added to the active set.

## Adding a New Command

1. Create a handler function in `features/commands/handlers/` (add a new file or append to an existing one):

```python
from features.commands.registry import CommandContext

async def handle_my_command(ctx: CommandContext, args: str) -> None:
    ctx.write_system(f"You ran my-command with args: {args}")
```

2. Register it in `features/commands/__init__.py`:

```python
from features.commands.handlers.my_module import handle_my_command

def register_all_commands(registry: CommandRegistry) -> None:
    # ... existing registrations ...
    registry.register(Command(
        name="my-command",
        description="Does something useful",
        handler=handle_my_command,
    ))
```

That's all — the command is now available as `/my-command` in the app.

## Design Notes

- **No cross-feature imports**: `features/commands` never imports from `features/skills`. The `SkillsManagerProtocol` in `registry.py` is the only coupling point — it's a structural interface, not a concrete dependency.
- **Fallback for dynamic names**: skill names come from `.md` files on disk and aren't known at registration time. Rather than re-registering on every load, a single fallback handler receives all unmatched commands and checks against the live skill list at dispatch time.
- **`extras` dict**: `CommandContext.extras` is reserved for future handlers that need context beyond what's currently defined. Add keys there rather than adding fields to the dataclass to avoid breaking existing handlers.
