from collections.abc import Callable
from typing import Awaitable

from features.commands.registry import Command, CommandContext


def make_help_handler(
    get_commands: Callable[[], dict[str, Command]],
) -> Callable[[CommandContext, str], Awaitable[None]]:
    async def handle_help(ctx: CommandContext, args: str) -> None:
        ctx.write_system("Available commands:")
        for cmd in get_commands().values():
            ctx.log.write(f"  [bold cyan]/{cmd.name}[/bold cyan] — {cmd.description}")
        # fallback pattern is not in registry.commands; show it as a static entry
        ctx.log.write(
            "  [bold cyan]/<skill-name>[/bold cyan] [dim][message][/dim]"
            " — Activate a skill persistently, or send a one-off message using it inline\n"
        )

    return handle_help
