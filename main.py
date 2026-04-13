"""
AI Agent TUI — Textual UI + Ollama + MCP tools.
Run: python main.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import override

import ollama

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, RichLog

from typing_extensions import final

MODEL = "qwen2.5:7b"  # change to any Ollama model you have pulled
SERVER_SCRIPT = Path(__file__).parent / "mcp_server.py"
SYSTEM_PROMPT = "You are a helpful assistant. Use tools when they help."


@final
class ChatApp(App):
    """Minimal Textual chat app."""

    TITLE = "AI Agent TUI"
    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self, session: ClientSession, tools: list, **kwargs) -> None:
        super().__init__(**kwargs)
        self.session = session
        self.tools = tools  # Ollama-format tool definitions
        self.history: list[dict] = []

    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log", markup=True, wrap=True)
        yield Input(placeholder="Type a message and press Enter…")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        tool_names = [t["function"]["name"] for t in self.tools] if self.tools else []
        if tool_names:
            log.write(f"[dim]Tools: {', '.join(tool_names)}[/dim]\n")
        else:
            log.write("[dim]No tools loaded (add .py files to plugins/)[/dim]\n")
        self.query_one(Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        log = self.query_one(RichLog)
        log.write(f"[bold cyan]You:[/bold cyan] {text}\n")
        self.history.append({"role": "user", "content": text})

        # Run the agentic loop in a worker so the UI stays responsive
        self.run_worker(self._agent_turn(log), exclusive=True)

    async def _agent_turn(self, log: RichLog) -> None:
        """Agentic loop: call Ollama, handle tool calls, repeat."""
        while True:
            response = ollama.chat(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.history,
                tools=self.tools or None,
            )
            msg = response.message
            self.history.append(msg)

            # Print any text content
            if msg.content:
                log.write(f"[bold green]Assistant:[/bold green] {msg.content}\n")

            # No tool calls → we're done
            if not msg.tool_calls:
                break

            # Handle tool calls
            for call in msg.tool_calls:
                name = call.function.name
                args = call.function.arguments  # already a dict from ollama client
                log.write(f"[dim]  🔧 {name}({json.dumps(args)})[/dim]")
                try:
                    result = await self.session.call_tool(name, args)
                    result_text = (
                        result.content[0].text
                        if result.content and hasattr(result.content[0], "text")
                        else str(result.content)
                    )
                    log.write("[dim]  ✓ done[/dim]\n")
                except Exception as e:
                    result_text = f"Error: {e}"
                    log.write(f"[dim]  ✗ {e}[/dim]\n")

                self.history.append(
                    {
                        "role": "tool",
                        "content": result_text,
                    }
                )


async def run() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Fetch tools from MCP and convert to Ollama format
            tools_response = await session.list_tools()
            mcp_tools = tools_response.tools

            ollama_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema,
                    },
                }
                for t in mcp_tools
            ]

            app = ChatApp(session=session, tools=ollama_tools)
            await app.run_async()


if __name__ == "__main__":
    asyncio.run(run())
