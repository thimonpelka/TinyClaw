from features.commands.handlers.help_commands import make_help_handler
from features.commands.handlers.skills_commands import (
    handle_disable_skills,
    handle_list_skills,
    handle_skill_by_name,
)
from features.commands.registry import Command, CommandContext, CommandRegistry


def register_all_commands(registry: CommandRegistry) -> None:
    registry.register(Command(
        name="help",
        description="List all available commands and how to use them",
        handler=make_help_handler(lambda: registry.commands),
    ))
    registry.register(Command(
        name="skills",
        description="List all available skills and their active status",
        handler=handle_list_skills,
    ))
    registry.register(Command(
        name="disable-skills",
        description="Deactivate a named skill, or all skills if no name given",
        handler=handle_disable_skills,
    ))
    registry.register_fallback(Command(
        name="_skill_fallback",
        description="Activate or inline-use a skill by name",
        handler=handle_skill_by_name,
    ))


__all__ = ["Command", "CommandContext", "CommandRegistry", "register_all_commands"]
