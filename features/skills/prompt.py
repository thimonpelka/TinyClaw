from features.skills.types import Skill


def build_system_prompt(skills: list[Skill]) -> str:
    base = "You are a helpful assistant. Use tools when they help. You can call multiple tools one after each other. If two tool calls are depended on each other then just call the first one and you will get the opportunity to call the second call after you get the respose. If they are independent of each other you can call them at the same time."
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
