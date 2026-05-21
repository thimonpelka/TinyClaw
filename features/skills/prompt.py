from features.skills.types import Skill


def build_system_prompt(skills: list[Skill]) -> str:
    base = "You are a helpful assistant. Use tools when they help."
    if not skills:
        return base
    lines = [
        base,
        "",
        "## Available Skills",
        "Load a skill's full guidance with the `use_skill` tool when relevant.",
    ]
    for s in skills:
        lines.append(
            f"- **{s['name']}**: {s['description']} (use when: {s['when_to_use']})"
        )
    return "\n".join(lines)
