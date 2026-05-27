from features.skills.types import Skill


def build_system_prompt(skills: list[Skill]) -> str:
    lines = ["You are a helpful assistant. Use tools when they help."]
    if skills:
        lines += [
            "",
            "## Available Skills",
            "Load a skill's full guidance with the `use_skill` tool when relevant.",
        ]
        for s in skills:
            lines.append(
                f"- **{s['name']}**: {s['description']} (use when: {s['when_to_use']})"
            )
    lines += [
        "",
        "## Memory",
        "Persistent memory is available at `.memory/memory_overview.md`.",
        "Use `read_memory_overview` to see what's stored, `read_memory_file` to load a specific",
        "memory, `save_memory` to create a new one, and `update_memory` to revise an existing one.",
        "Consult memory proactively when context about the user, project, or past sessions would help.",
    ]
    return "\n".join(lines)
