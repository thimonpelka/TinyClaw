from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"


@mcp.tool()
def use_skill(name: str) -> str:
    """Load the full guidance content of a named skill. Call this when the system prompt indicates a skill is relevant."""
    path = SKILLS_DIR / f"{name}.md"
    if not path.exists():
        available = [p.stem for p in sorted(SKILLS_DIR.glob("*.md"))]
        return f"Skill '{name}' not found. Available: {', '.join(available)}"
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text
