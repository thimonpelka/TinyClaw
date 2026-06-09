import json
import os
from collections.abc import Callable

import httpx

from .protocol import LLMMessage, ToolCall

_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider:
    def __init__(self) -> None:
        self._api_key = os.environ.get("OPENROUTER_API_KEY", "")

    async def ensure_ready(
        self,
        model: str,
        on_log: Callable[[str], None] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        if not self._api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Add it to your .env file."
            )
        if on_log:
            on_log(f"OpenRouter ready (model: {model})")

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        model: str,
    ) -> LLMMessage:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {"model": model, "messages": messages}
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        raw_msg = data["choices"][0]["message"]
        raw_tool_calls = raw_msg.get("tool_calls")

        tool_calls = None
        if raw_tool_calls:
            tool_calls = [
                ToolCall(
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"]),
                    id=tc.get("id", ""),
                )
                for tc in raw_tool_calls
            ]

        history_entry: dict = {"role": "assistant", "content": raw_msg.get("content")}
        if raw_tool_calls:
            history_entry["tool_calls"] = raw_tool_calls

        return LLMMessage(
            content=raw_msg.get("content"),
            tool_calls=tool_calls,
            history_entry=history_entry,
        )

    def make_tool_result(self, tool_call: ToolCall, content: str) -> dict:
        result: dict = {"role": "tool", "content": content}
        if tool_call.id:
            result["tool_call_id"] = tool_call.id
        return result

    def shutdown(self) -> None:
        pass
