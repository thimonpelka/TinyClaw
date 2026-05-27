from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path(__file__).parent.parent / ".memory"
OVERVIEW_FILE = MEMORY_DIR / "memory_overview.md"


def _safe_path(filename: str) -> Path | None:
    """Return the resolved path only if it stays inside MEMORY_DIR."""
    target = (MEMORY_DIR / filename).resolve()
    try:
        target.relative_to(MEMORY_DIR.resolve())
        return target
    except ValueError:
        return None


def _update_overview(filename: str, summary: str) -> None:
    """Insert or replace the overview entry for filename."""
    today = datetime.now().strftime("%Y-%m-%d")
    new_line = f"- **{filename}** — {summary} (updated: {today})"

    if not OVERVIEW_FILE.exists():
        OVERVIEW_FILE.write_text("# Memory Overview\n\n" + new_line + "\n", encoding="utf-8")
        return

    text = OVERVIEW_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(f"- **{filename}**"):
            lines[i] = new_line
            replaced = True
            break

    if not replaced:
        # Remove placeholder if present, then append
        lines = [l for l in lines if l.strip() != "No memories saved yet."]
        lines.append(new_line)

    OVERVIEW_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


@mcp.tool()
def read_memory_overview() -> str:
    """Read the memory overview listing all saved memory files and their summaries."""
    if not OVERVIEW_FILE.exists():
        return "No memory overview found. No memories have been saved yet."
    return OVERVIEW_FILE.read_text(encoding="utf-8")


@mcp.tool()
def read_memory_file(filename: str) -> str:
    """Read the contents of a specific memory file. Pass the filename (e.g. 'user-preferences.md')."""
    path = _safe_path(filename)
    if path is None:
        return f"Invalid filename: '{filename}'. Must not contain path traversal."
    if not path.exists():
        available = [p.name for p in sorted(MEMORY_DIR.glob("*.md")) if p.name != "memory_overview.md"]
        return f"Memory file '{filename}' not found. Available: {', '.join(available) or 'none'}"
    return path.read_text(encoding="utf-8")


@mcp.tool()
def save_memory(filename: str, content: str, summary: str) -> str:
    """Create a new memory file. filename should be kebab-case with .md extension (e.g. 'user-preferences.md').
    content is the full markdown body. summary is a short one-line description for the overview index."""
    path = _safe_path(filename)
    if path is None:
        return f"Invalid filename: '{filename}'. Must not contain path traversal."
    if path.exists():
        return f"Memory file '{filename}' already exists. Use update_memory to modify it."

    now = datetime.now().isoformat(timespec="seconds")
    name_stem = Path(filename).stem
    file_content = f"---\nname: {name_stem}\ncreated: {now}\nlast_updated: {now}\n---\n\n{content}\n"
    path.write_text(file_content, encoding="utf-8")
    _update_overview(filename, summary)
    return f"Memory saved to '{filename}' and overview updated."


@mcp.tool()
def update_memory(filename: str, content: str, new_summary: str | None = None) -> str:
    """Update an existing memory file with new content. Optionally update its summary in the overview.
    Returns an error if the file doesn't exist — use save_memory to create new files."""
    path = _safe_path(filename)
    if path is None:
        return f"Invalid filename: '{filename}'. Must not contain path traversal."
    if not path.exists():
        return f"Memory file '{filename}' not found. Use save_memory to create a new memory."

    existing = path.read_text(encoding="utf-8")
    now = datetime.now().isoformat(timespec="seconds")

    # Update last_updated in frontmatter if present
    if existing.startswith("---"):
        parts = existing.split("---", 2)
        if len(parts) == 3:
            frontmatter = parts[1]
            body = parts[2]
            if "last_updated:" in frontmatter:
                lines = frontmatter.splitlines()
                frontmatter = "\n".join(
                    f"last_updated: {now}" if l.startswith("last_updated:") else l
                    for l in lines
                )
            else:
                frontmatter = frontmatter.rstrip() + f"\nlast_updated: {now}"
            existing = f"---{frontmatter}---\n\n{content}\n"
        else:
            existing = f"---\nlast_updated: {now}\n---\n\n{content}\n"
    else:
        existing = f"---\nlast_updated: {now}\n---\n\n{content}\n"

    path.write_text(existing, encoding="utf-8")
    if new_summary:
        _update_overview(filename, new_summary)
    return f"Memory '{filename}' updated." + (" Overview entry updated." if new_summary else "")
