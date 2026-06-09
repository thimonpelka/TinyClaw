import asyncio
import subprocess

import httpx
import ollama as _ollama

from .protocol import LLMMessage, ToolCall

_BASE_URL = "http://localhost:11434"


class OllamaProvider:
    def __init__(self) -> None:
        self._process: subprocess.Popen[bytes] | None = None

    async def ensure_ready(self, model: str) -> None:
        await self._start_server()
        await self._pull_model(model)

    async def _start_server(self) -> None:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{_BASE_URL}/api/tags", timeout=2)
            return
        except Exception:
            pass

        self._process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        for _ in range(20):
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{_BASE_URL}/api/tags", timeout=2)
                return
            except Exception:
                await asyncio.sleep(0.5)

        raise RuntimeError("Ollama did not start within 10 seconds")

    async def _pull_model(self, model: str) -> None:
        models = await _ollama.AsyncClient().list()
        names = [m.model for m in models.models]
        if model in names:
            return
        try:
            async for _ in await _ollama.AsyncClient().pull(model, stream=True):
                pass
        except _ollama.ResponseError as e:
            raise RuntimeError(f"Failed to pull model '{model}': {e}") from e

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        model: str,
    ) -> LLMMessage:
        response = await _ollama.AsyncClient().chat(
            model=model,
            messages=messages,
            tools=tools or None,
        )
        msg = response.message

        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                ToolCall(name=tc.function.name, arguments=dict(tc.function.arguments))
                for tc in msg.tool_calls
            ]

        history_entry: dict = {"role": "assistant", "content": msg.content or ""}
        if tool_calls:
            history_entry["tool_calls"] = [
                {"function": {"name": tc.name, "arguments": tc.arguments}}
                for tc in tool_calls
            ]

        return LLMMessage(
            content=msg.content,
            tool_calls=tool_calls,
            history_entry=history_entry,
        )

    def make_tool_result(self, tool_call: ToolCall, content: str) -> dict:
        return {"role": "tool", "content": content}

    def shutdown(self) -> None:
        if self._process is None:
            return
        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        except Exception:
            pass
        self._process = None
