from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol

from rich.text import Text
from textual.widgets import RichLog


class SkillsManagerProtocol(Protocol):
    @property
    def skills(self) -> list: ...

    @property
    def active_skill_names(self) -> list[str]: ...

    def find(self, name: str) -> Any: ...

    def activate(self, name: str) -> bool: ...

    def deactivate(self, name: str) -> bool: ...

    def deactivate_all(self) -> None: ...

    def build_prefix(self, extra_names: list[str] | None = None) -> str: ...

    def badge_markup(self, name: str) -> str: ...

    def indicator_text(self) -> Text: ...

    def list_renderables(self) -> list[tuple[str, str, str]]: ...


@dataclass
class CommandContext:
    log: RichLog
    write_system: Callable[[str], None]
    write_error: Callable[[str], None]
    send_message: Callable[[str, str], None]
    update_indicator: Callable[[], None]
    skills: SkillsManagerProtocol
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class Command:
    name: str
    description: str
    handler: Callable[[CommandContext, str], Awaitable[None]]


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._fallback: Command | None = None

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def register_fallback(self, command: Command) -> None:
        self._fallback = command

    async def dispatch(self, raw: str, ctx: CommandContext) -> bool:
        """Parse raw (text after '/'), dispatch to matching command or fallback.
        Returns True if handled, False if unknown."""
        parts = raw.split(" ", 1)
        name = parts[0]
        args = parts[1].strip() if len(parts) > 1 else ""
        command = self._commands.get(name)
        if command is not None:
            await command.handler(ctx, args)
            return True
        if self._fallback is not None:
            await self._fallback.handler(ctx, raw)
            return True
        return False

    @property
    def commands(self) -> dict[str, Command]:
        return dict(self._commands)
