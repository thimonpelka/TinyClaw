from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str = ""


@dataclass
class LLMMessage:
    content: str | None
    tool_calls: list[ToolCall] | None
    # Provider-specific dict to append to conversation history.
    # Each provider serializes assistant turns differently (Ollama vs OpenAI format),
    # so the provider owns this entry rather than the app normalizing it.
    history_entry: dict = field(default_factory=dict)


class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        model: str,
    ) -> LLMMessage: ...

    def make_tool_result(self, tool_call: ToolCall, content: str) -> dict: ...

    async def ensure_ready(self, model: str) -> None: ...

    def shutdown(self) -> None: ...
