import asyncio
import subprocess
from collections.abc import Callable

import httpx
import ollama as _ollama

from .protocol import LLMMessage, ToolCall

_BASE_URL = "http://localhost:11434"


class OllamaProvider:
    def __init__(self) -> None:
        self._process: subprocess.Popen[bytes] | None = None

    async def ensure_ready(
        self,
        model: str,
        on_log: Callable[[str], None] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        await self._start_server(on_log)
        await self._pull_model(model, on_log, on_progress)

    async def _start_server(self, on_log: Callable[[str], None] | None = None) -> None:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{_BASE_URL}/api/tags", timeout=2)
            if on_log:
                on_log("Ollama is already running.")
            return
        except Exception:
            pass

        if on_log:
            on_log("Starting Ollama server...")
        self._process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        for _ in range(20):
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{_BASE_URL}/api/tags", timeout=2)
                if on_log:
                    on_log("Ollama started.")
                return
            except Exception:
                await asyncio.sleep(0.5)

        raise RuntimeError("Ollama did not start within 10 seconds")

    async def _pull_model(
        self,
        model: str,
        on_log: Callable[[str], None] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        models = await _ollama.AsyncClient().list()
        names = [m.model for m in models.models]
        if model in names:
            if on_log:
                on_log(f"Model ready: {model}")
            return

        if on_log:
            on_log(f"Downloading {model} — this may take a while...")

        last_status = ""
        try:
            async for progress in await _ollama.AsyncClient().pull(model, stream=True):
                if progress.total and progress.completed and on_progress:
                    pct = int(progress.completed / progress.total * 100)
                    on_progress(f"[bold cyan]⬇ Downloading {model}: {pct}%[/]")
                elif progress.status and progress.status != last_status:
                    last_status = progress.status
                    if on_log:
                        on_log(progress.status)
        except _ollama.ResponseError as e:
            raise RuntimeError(f"Failed to pull model '{model}': {e}") from e

        if on_progress:
            on_progress("")  # clear the progress label
        if on_log:
            on_log(f"Model downloaded: {model}")

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
