# features/skills

This package owns all skills state and logic: loading skill files from disk, building system prompt injections, tracking which skills are active, and rendering skill badges in the UI.

## Concepts

A **skill** is a Markdown file in the `skill-definitions/` directory at the repo root. It contains a YAML frontmatter block with metadata and a body with full behavioral guidance. Skills give the agent specialized instructions for particular tasks — they are injected into the conversation only when relevant, keeping context lean by default.

Skills can be used in three ways:

| Mode | How | Effect |
|------|-----|--------|
| **Agent-autonomous** | Agent calls `use_skill("<name>")` MCP tool | Skill body injected into that turn |
| **Inline** | User types `/<skill-name> <message>` | Skill prepended to that message only |
| **Persistent** | User types `/<skill-name>` (no message) | Skill prepended to every message until deactivated |

Multiple persistent skills can be active simultaneously. Active skills are applied in activation order. An inline skill applies on top of any currently active persistent skills.

## Skill File Format

```
skill-definitions/my-skill.md
```

```markdown
---
name: my-skill
description: One-sentence description shown to the agent in the system prompt
when_to_use: Describe the conditions under which this skill is relevant
---

# My Skill

Full behavioral guidance. The agent reads this content when the skill is loaded.
Write clear, imperative instructions — tell the agent exactly how to behave.
```

**Frontmatter fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Identifier used in slash commands and system prompt. Use kebab-case. |
| `description` | Yes | Short description injected into the system prompt so the agent knows the skill exists. |
| `when_to_use` | Yes | Guidance on when the agent should autonomously load this skill. |

The body (everything after the second `---`) is the full skill content. It is loaded into the conversation only when the skill is activated — not on every message.

## Package Structure

```
features/skills/
├── __init__.py      # Public exports: SkillsManager, Skill
├── types.py         # Skill TypedDict
├── colors.py        # Deterministic per-name badge colors
├── loader.py        # load_skills(dir) → list[Skill]
├── prompt.py        # build_system_prompt(skills) → str
└── manager.py       # SkillsManager class
```

## SkillsManager

`SkillsManager` is the single owner of all runtime skills state. It is instantiated once in `ChatApp.__init__` and injected into `CommandContext` for use by command handlers.

```python
from features.skills import SkillsManager
from pathlib import Path

manager = SkillsManager(Path("skills"))
manager.load()  # reads all .md files from disk
```

**Key methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `load()` | `None` | Reads all `.md` files from `skills_dir` and populates the internal skill list. Call once on startup. |
| `find(name)` | `Skill \| None` | Looks up a skill by name. Returns `None` if not found. |
| `activate(name)` | `bool` | Adds skill to the active set. Returns `False` if already active. Raises `ValueError` if skill not found. |
| `deactivate(name)` | `bool` | Removes skill from the active set. Returns `False` if not active. |
| `deactivate_all()` | `None` | Clears all active skills. |
| `build_prefix(extra_names?)` | `str` | Builds the block prepended to user messages. Combines all active skills plus any `extra_names` (used for inline one-shot skills). |
| `system_prompt()` | `str` | Returns the full system prompt string, which includes skill names/descriptions for agent discovery. |
| `indicator_text()` | `rich.text.Text` | Returns a styled `Text` object for the `#skillsStatus` label in the UI. |
| `list_renderables()` | `list[tuple[str, str, str]]` | Returns `(badge_markup, description, when_to_use)` for each loaded skill. Used by `/skills` command. |
| `badge_markup(name)` | `str` | Returns a Rich markup string for a single skill badge. |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `skills` | `list[Skill]` | All loaded skills (regardless of active state). |
| `active_skill_names` | `list[str]` | Names of currently active skills, in activation order. |

## Colors

Skill badge colors are assigned deterministically by name using MD5:

```python
# features/skills/colors.py
idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(SKILL_BADGE_COLORS)
```

This means the same skill always gets the same color across restarts and across different machines. The color palette has 7 entries drawn from a Tokyo Night-inspired set.

## System Prompt Injection

On startup, all skill metadata is injected into the system prompt so the agent knows which skills exist without loading their full content:

```
You are a helpful assistant. Use tools when they help.

## Available Skills
Load a skill's full guidance with the `use_skill` tool when relevant.
- **my-skill**: One-sentence description (use when: ...)
```

The agent can then call the `use_skill` MCP tool (defined in `plugins/skills.py`) to load the full body of a skill when it decides it's relevant.

## Adding a New Skill

1. Create a file in `skill-definitions/` with a `.md` extension.
2. Add the frontmatter block with `name`, `description`, and `when_to_use`.
3. Write the guidance body below the second `---`.
4. Restart TinyClaw — the skill is automatically picked up on `SkillsManager.load()`.

No code changes required.
