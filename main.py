import asyncio
import hashlib
import subprocess
import httpx
import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import override

import ollama
from rich.text import Text
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Label
from typing_extensions import final

from custom_types import CommandHistory, OllamaTool, Mode, Skill

SERVER_SCRIPT = Path(__file__).parent / "mcp_server.py"
SKILLS_DIR = Path(__file__).parent / "skills"
MAX_STEPS = 8
MAX_HISTORY = 20

SKILL_BADGE_COLORS = [
    "#7aa2f7",  # blue
    "#9ece6a",  # green
    "#e0af68",  # yellow
    "#bb9af7",  # purple
    "#f7768e",  # red
    "#2ac3de",  # cyan
    "#ff9e64",  # orange
]


def _skill_color(name: str) -> str:
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(SKILL_BADGE_COLORS)
    return SKILL_BADGE_COLORS[idx]


def load_skills() -> list[Skill]:
    skills: list[Skill] = []
    if not SKILLS_DIR.exists():
        return skills
    for path in sorted(SKILLS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                fm, body = parts[1], parts[2]
                meta: dict[str, str] = {}
                for line in fm.strip().splitlines():
                    if ": " in line:
                        k, v = line.split(": ", 1)
                        meta[k.strip()] = v.strip()
                skills.append(
                    Skill(
                        name=meta.get("name", path.stem),
                        description=meta.get("description", ""),
                        when_to_use=meta.get("when_to_use", ""),
                        content=body.strip(),
                    )
                )
    return skills


def build_system_prompt(skills: list[Skill]) -> str:
    base = "You are a helpful assistant. Use tools when they help."
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

ASCII_LOGO = """
████████╗██╗███╗   ██╗██╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
╚══██╔══╝██║████╗  ██║╚██╗ ██╔╝██╔════╝██║     ██╔══██╗██║    ██║
   ██║   ██║██╔██╗ ██║ ╚████╔╝ ██║     ██║     ███████║██║ █╗ ██║
   ██║   ██║██║╚██╗██║  ╚██╔╝  ██║     ██║     ██╔══██║██║███╗██║
   ██║   ██║██║ ╚████║   ██║   ╚██████╗███████╗██║  ██║╚███╔███╔╝
   ╚═╝   ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ 
"""

OLLAMA_URL = "http://localhost:11434"


@final
class ChatApp(App):
    """Minimal Textual chat app."""

    CSS_PATH = "app.css"

    TITLE = "TinyClaw"
    SUB_TITLE = "Your personal assistant"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("i", "enter_insert", "Insert mode"),
        ("escape", "enter_normal", "Normal mode"),
        ("t", "show_tools", "Show tools"),
        ("s", "show_skills", "Skills"),
        ("c", "clear_chat", "Clear"),
        ("u", "scroll_up", "Scroll Up"),
        ("d", "scroll_down", "Scroll Down"),
    ]

    model = "qwen2.5:7b"  # TODO: change to other ollama models for testing
    mode: Mode
    debug_active: bool
    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    tool_names: list[str] = []

    ollama_ready: bool = False
    model_ready: bool = False
    ollama_process: subprocess.Popen[bytes] | None = None
    ollama_running_locally: bool = True

    def __init__(
        self,
        session: ClientSession,
        tools: list[OllamaTool],
        args: Namespace,
        system_prompt: str,
        skills: list[Skill],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.session = session

        self.tools = tools
        self.tool_names = [tool["function"]["name"] for tool in tools]

        self.history: list[CommandHistory] = []
        self.mode = Mode.NORMAL
        self.debug_active = args.debug  # pyright: ignore[reportAny]

        self.system_prompt = system_prompt
        self.skills = skills
        self._active_skills: list[str] = []

        print(args.model)
        if args.model is not None:
            print(args.model)
            self.model = args.model

        self.loading = False
        self.spinner_frame = 0
        self.spinner_task = None

    def write_user(self, log: RichLog, text: str) -> None:
        """
        Helper function for messages by the user

        Args:
            log: log object to print to
            text: text to print
        """

        log.write("\n[bold #7aa2f7]You[/bold #7aa2f7]")
        log.write(f"[#c0caf5]{text}[/]\n")
        log.scroll_end(animate=False)

    def write_system(self, log: RichLog, text: str) -> None:
        """
        Helper function for system messages

        Args:
            log: log object to print to
            text: text to print
        """

        log.write(f"[dim]{text}[/dim]\n")
        log.scroll_end(animate=False)

    def write_error(self, log: RichLog, text: str) -> None:
        """
        Helper function for system errors

        Args:
            log: log object to print to
            text: text to print
        """

        log.write(f"[bold #8B0000]{text}[/bold #8B0000]\n")
        log.scroll_end(animate=False)

    def write_assistant(self, log: RichLog, text: str) -> None:
        """
        Helper function for messages by the llm ("assistant")

        Args:
            log: log object to print to
            text: text to print
        """

        log.write(f"\n[bold #9ece6a]{self.TITLE}[/bold #9ece6a]")
        log.write(f"[#c0caf5]{text}[/]\n")
        log.scroll_end(animate=False)

    @override
    def compose(self) -> ComposeResult:
        """

        Sets up the TUI Layout and all available Widgets

        Yields: TUI Layout

        """
        yield Header(show_clock=False, icon="")
        with Vertical():
            yield RichLog(id="log", markup=True, wrap=True)
            yield RichLog(id="tools", markup=True, wrap=True)
            yield Label("", id="loadingStatus")
            yield Input(placeholder="Type a message and press Enter…")
            yield Label("", id="skillsStatus")
        with Horizontal(id="footer-outer"):
            yield Label("", id="status")
            with Horizontal(id="footer-inner"):
                yield Footer(show_command_palette=False)

    async def ensure_ollama_running(self, log: RichLog) -> None:
        """
        Ensure that ollama is running and ready for communication.

        Args:
            log: log to print info to
        """
        self.write_system(log, "Checking availability of ollama...")
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{OLLAMA_URL}/api/tags", timeout=2)
            self.write_system(log, "Ollama is already running. Great!")
            self.ollama_ready = True
            return
        except Exception:
            self.write_system(log, "Ollama not yet running. Starting Ollama...")

        # Start ollama process
        self.ollama_process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.ollama_running_locally = True

        # Wait until it's ready
        for _ in range(20):
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{OLLAMA_URL}/api/tags", timeout=2)
                self.write_system(log, "Ollama started successfully!")
                self.ollama_ready = True
                return
            except Exception:
                await asyncio.sleep(0.5)

        raise RuntimeError("Failed to start Ollama")

    async def ensure_model(self, log: RichLog) -> None:
        """
        Ensure that the selected model is installed and ready.

        Args:
            log: log to print info to
        """
        self.write_system(log, f"Checking availability of model: {self.model}")

        models = await ollama.AsyncClient().list()
        names = [m.model for m in models.models]

        if self.model in names:
            self.model_ready = True
            self.write_system(
                log, f"Model already installed: {self.model}. Ready for operations!"
            )
            return

        self.write_system(
            log, f"Model not found. Pulling: {self.model} (this may take a while...)"
        )

        # Pull model with progress
        try:
            async for progress in await ollama.AsyncClient().pull(self.model, stream=True):
                if progress.status:
                    self.write_system(log, progress.status)
        except ollama.ResponseError as e:
            self.write_error(log, "Error while loading model. Please restart with a different model!")

            if self.debug_active:
                self.write_error(log, f"Error is: {e}")

            return

        self.write_system(log, f"Model installation complete: {self.model}")
        self.model_ready = True

    def update_status(self) -> None:
        """
        Updates the status bar with the current MODE
        """

        status = self.query_one("#status", Label)

        if self.mode == Mode.NORMAL:
            status.update("[bold yellow]NORMAL[/]")
        elif self.mode == Mode.INSERT:
            status.update("[bold green]INSERT[/]")
        elif self.mode == Mode.TOOLS:
            status.update("[bold magenta]TOOLS[/]")

    def add_to_history(self, new_item: CommandHistory) -> None:
        """
        Add an entry to the history. Automatically cuts of the history at max defined length

        Args:
            new_item: item to add to history
        """

        self.history.append(new_item)

        if len(self.history) > MAX_HISTORY:
            # TODO: Possible improvement: Instead of just cutting it we could tell the LLM to summarize the last few history items.
            # e.g. once it reaches MAX_HISTORY. it should summarize the last 5 messages into one.
            self.history = self.history[-MAX_HISTORY:]

    async def on_unmount(self) -> None:
        """
        Gets called on unmount of app. Shuts down ollama if started by the app.
        """

        if self.ollama_running_locally and self.ollama_process:
            print("Shutting down Ollama...")

            try:
                self.ollama_process.terminate()

                try:
                    self.ollama_process.wait(timeout=5)
                    print("Ollama stopped successfully!")
                except subprocess.TimeoutExpired:
                    print("Ollama did not stop in time. Killing it...")
                    self.ollama_process.kill()

            except Exception as e:
                print(f"Failed to stop Ollama: {e}")

    async def on_mount(self) -> None:
        """
        On mount print the list of tools loaded from the MCP
        """

        log = self.query_one("#log", RichLog)

        tool_names = [t["function"]["name"] for t in self.tools] if self.tools else []

        tools_view = self.query_one("#tools", RichLog)
        tools_view.display = False

        loading_label = self.query_one("#loadingStatus", Label)
        loading_label.display = False

        self.query_one("#skillsStatus", Label).update(
            "[dim]No active skills  ·  press s to browse  ·  /skill-name to activate[/dim]"
        )

        self.write_system(log, ASCII_LOGO)

        if self.debug_active:
            self.write_system(log, "Debug mode is active. Expect detailed logs.")

        if tool_names:
            self.write_system(log, f"Succesfully loaded tools: {', '.join(tool_names)}")
        else:
            self.write_system(log, "No tools loaded (add .py files to plugins/)")

        self.update_status()

        self.run_worker(
            self._ensure_readiness(log),
            exclusive=True,  # makes it so that the previous request gets cancelled upon a new request!
            thread=False,
        )

    async def _ensure_readiness(self, log: RichLog) -> None:

        await self.ensure_ollama_running(log)
        await self.ensure_model(log)

        if self.ollama_ready and self.model_ready:
            self.write_system(log, f"{self.TITLE} is ready for you! Press 'i' to interact.")

    def start_loading(self) -> None:
        self.loading = True
        self.spinner_frame = 0

        def tick() -> None:
            if not self.loading:
                return

            label = self.query_one("#loadingStatus", Label)
            label.display = True
            frame = self.SPINNER[self.spinner_frame % len(self.SPINNER)]
            label.update(f"[bold cyan]{frame} Thinking...[/]")

            self.spinner_frame += 1

        self.spinner_task = self.set_interval(0.1, tick)

    def stop_loading(self) -> None:
        self.loading = False

        if self.spinner_task:
            self.spinner_task.stop()
            label = self.query_one("#loadingStatus", Label)
            label.display = False
            self.spinner_task = None

        self.update_status()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Input handler. Handles input field submission. Runs agent with request in thread.

        Args:
            event: Input event by Textual
        """

        # Only allow typing while in insert mode!
        if self.mode != Mode.INSERT:
            return

        log = self.query_one("#log", RichLog)

        if not self.ollama_ready:
            self.write_system(
                log, "Ollama is not yet ready for operations. Please wait..."
            )
            return

        if not self.model_ready:
            self.write_system(
                log, "The ollama model is not yet ready for operations. Please wait..."
            )
            return

        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/"):
            await self._handle_slash_command(text[1:], log)
            return

        prefix = self._build_skill_prefix(self._active_skills)
        full_text = f"{prefix}\n\n---\n\n{text}" if prefix else text
        self._send_message(text, full_text, log)

    def _send_message(self, display_text: str, full_text: str, log: RichLog) -> None:
        self.write_user(log, display_text)
        self.add_to_history({"role": "user", "content": full_text})
        self.run_worker(
            self._agent_turn(log),
            exclusive=True,
            thread=False,
        )

    def _build_skill_prefix(self, names: list[str]) -> str:
        parts = []
        for name in names:
            skill = next((s for s in self.skills if s["name"] == name), None)
            if skill:
                parts.append(f"# [Skill: {name}]\n{skill['content']}")
        return "\n\n---\n\n".join(parts)

    def _update_skills_indicator(self) -> None:
        label = self.query_one("#skillsStatus", Label)
        if self._active_skills:
            text = Text()
            for i, name in enumerate(self._active_skills):
                if i > 0:
                    text.append("  ")
                text.append(f" {name} ", style=f"bold {_skill_color(name)}")
            label.update(text)
        else:
            label.update(
                "[dim]No active skills  ·  press s to browse  ·  /skill-name to activate[/dim]"
            )

    async def _handle_slash_command(self, command: str, log: RichLog) -> None:
        # /skills — list available
        if command == "skills":
            if not self.skills:
                self.write_system(log, "No skills loaded (add .md files to skills/)")
                return
            self.write_system(log, "Available skills:")
            for s in self.skills:
                color = _skill_color(s["name"])
                log.write(f"  [bold {color}][ {s['name']} ][/] — {s['description']}")
            return

        # /disable-skills [skill-name]
        if command == "disable-skills" or command.startswith("disable-skills "):
            parts = command.split(" ", 1)
            if len(parts) == 1:
                self._active_skills.clear()
                self.write_system(log, "All skills deactivated.")
            else:
                name = parts[1].strip()
                if name in self._active_skills:
                    self._active_skills.remove(name)
                    self.write_system(log, f"Skill [cyan]{name}[/cyan] deactivated.")
                else:
                    self.write_error(log, f"Skill '{name}' is not currently active.")
            self._update_skills_indicator()
            return

        # /skill-name [inline message]
        parts = command.split(" ", 1)
        skill_name = parts[0]
        inline_message = parts[1].strip() if len(parts) > 1 else None

        skill = next((s for s in self.skills if s["name"] == skill_name), None)
        if skill is None:
            self.write_error(log, f"Unknown command: /{command}")
            return

        if inline_message:
            # One-shot: persistent skills + this inline skill for this message only
            names_for_message = self._active_skills + [skill_name]
            prefix = self._build_skill_prefix(names_for_message)
            full_text = f"{prefix}\n\n---\n\n{inline_message}"
            color = _skill_color(skill_name)
            display_text = f"[bold {color}][ {skill_name} ][/] {inline_message}"
            self._send_message(display_text, full_text, log)
        else:
            # Persistent: add to active skills
            if skill_name in self._active_skills:
                self.write_error(log, f"Skill '{skill_name}' is already active.")
                return
            self._active_skills.append(skill_name)
            self.write_system(
                log,
                f"Skill [cyan]{skill_name}[/cyan] activated — prepended to all future messages.",
            )
            self._update_skills_indicator()

    def action_enter_insert(self) -> None:
        """
        Action which gets called when the "enter_insert" event is triggered.
        Updates mode. Enables / Disables the required fields / widgets.
        """

        self.mode = Mode.INSERT

        tools_view = self.query_one("#tools")
        log = self.query_one("#log")

        tools_view.display = False
        log.display = True

        input_field = self.query_one(Input)
        input_field.disabled = False
        input_field.focus()
        input_field.placeholder = "Type a message..."

        self.update_status()

    def action_enter_normal(self) -> None:
        """
        Action which gets called when the "enter_normal" event is triggered.
        Updates mode. Enables / Disables the required fields / widgets.
        """

        self.mode = Mode.NORMAL

        tools_view = self.query_one("#tools")
        log = self.query_one("#log")

        tools_view.display = False
        log.display = True

        input_field = self.query_one(Input)
        input_field.disabled = True
        input_field.blur()

        self.update_status()

    def action_show_tools(self) -> None:
        """
        Action which gets called when the "show_tools" event is triggered.
        Updates mode. Enables / Disables the required fields / widgets.
        """

        self.mode = Mode.TOOLS

        tools_view = self.query_one("#tools", RichLog)
        log = self.query_one("#log")

        tools_view.display = True
        log.display = False

        tools_view.clear()

        for t in self.tools:
            fn = t["function"]
            tools_view.write(f"[bold #bb9af7]{fn['name']}[/]")
            self.write_system(tools_view, fn["description"])
            self.write_system(tools_view, json.dumps(fn["parameters"], indent=2))

        self.update_status()

    def action_show_skills(self) -> None:
        log = self.query_one("#log", RichLog)
        tools_view = self.query_one("#tools")

        tools_view.display = False
        log.display = True

        if not self.skills:
            self.write_system(log, "No skills loaded (add .md files to skills/)")
            return

        self.write_system(log, "Available skills  (active skills are highlighted):")
        for s in self.skills:
            color = _skill_color(s["name"])
            active_marker = " ●" if s["name"] in self._active_skills else ""
            log.write(
                f"  [bold {color}][ {s['name']}{active_marker} ][/]"
                f" — {s['description']}"
                f"  [dim](use when: {s['when_to_use']})[/dim]"
            )

    def action_clear_chat(self) -> None:
        """
        Action which gets called when the "clear_chat" event is triggered.
        Clears the history and the log.
        """

        self.history.clear()
        self.query_one("#log", RichLog).clear()

    def action_scroll_up(self) -> None:
        """
        Action which gets called when the "scroll_up" event is triggered.
        Scrolls the log up
        """

        if self.mode == Mode.NORMAL:
            log = self.query_one("#log")
            log.scroll_up()
        elif self.mode == Mode.TOOLS:
            log = self.query_one("#tools")
            log.scroll_up()

    def action_scroll_down(self) -> None:
        """
        Action which gets called when the "scroll_down" event is triggered.
        Scrolls the log down
        """

        if self.mode == Mode.NORMAL:
            log = self.query_one("#log")
            log.scroll_down()
        elif self.mode == Mode.TOOLS:
            log = self.query_one("#tools")
            log.scroll_down()

    async def _agent_turn(self, log: RichLog) -> None:
        """
        Agentic loop: call Ollama, handle tool calls, repeat.
        """

        self.action_enter_normal()
        self.start_loading()

        if self.debug_active:
            self.write_system(log, "Starting communication with Agent.")

        for step in range(
            MAX_STEPS
        ):  # loop until finished, but only for max MAX_STEPS to avoid infinite loop
            if self.debug_active:
                self.write_system(log, f"Communication iteration {step} with Agent")

            # Send request to ollama and wait for response
            response = await ollama.AsyncClient().chat(
                model=self.model,
                messages=[{"role": "system", "content": self.system_prompt}] + self.history,
                tools=self.tools or None,
            )
            msg = response.message

            if self.debug_active:
                self.write_system(log, str(msg))

            self.add_to_history(msg)  # pyright: ignore[reportArgumentType]

            # Print any text content
            if msg.content:
                self.write_assistant(log, msg.content)

            # No tool calls → we're done
            if not msg.tool_calls:
                break

            # Handle tool calls asynchronously
            tasks = [self._execute_tool(call, log) for call in msg.tool_calls]

            results = await asyncio.gather(*tasks)

            # retrieve all results and append to history
            for res in results:
                self.add_to_history(res)

            self.write_system(log, "All tool calls completed")

            if self.debug_active and step == (MAX_STEPS - 1):
                self.write_system(log, "Max steps reached. Stopping.")

        self.stop_loading()


    async def _execute_tool(
        self, call: ollama.Message.ToolCall, log: RichLog
    ) -> CommandHistory:
        """
        Executes a given tool as requested by the LLM

        Args:
            call: call object returned by LLM
            log: log to print the log to

        Returns: Response of service. (CommandHistory type)

        """
        name = call.function.name
        args = call.function.arguments

        if name not in self.tool_names:
            return {"role": "tool", "content": f"Error: Tool '{name}' does not exist"}

        self.write_system(log, f"Using tool: {name} ({json.dumps(args)})")

        try:
            result = await self.session.call_tool(name, args)  # pyright: ignore[reportArgumentType]

            result_text = (
                result.content[0].text
                if result.content and hasattr(result.content[0], "text")
                else str(result.content)
            )

            if self.debug_active:
                self.write_system(log, f"{name} → {result_text}")

            return {
                "role": "tool",
                "content": result_text,
            }

        except Exception as e:
            self.write_system(log, f"{name} failed: {e}")
            return {
                "role": "tool",
                "content": f"Error: {e}",
            }


async def run(args: Namespace) -> None:
    """
    Starts the MCP Server in the background.
    Gathers the list of tools available within our Agentic AI.
    Starts the TUI.
    """

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

            ollama_tools: list[OllamaTool] = [
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

            skills = load_skills()
            system_prompt = build_system_prompt(skills)

            # Start TUI (run in background)
            app = ChatApp(
                session=session,
                tools=ollama_tools,
                args=args,
                system_prompt=system_prompt,
                skills=skills,
            )
            await app.run_async()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        dest="debug",
        default=False,
        help="Print additional information to the log.",
    )

    parser.add_argument(
        "-m",
        "--model",
        dest="model",
        default=None,
        help="Specifically select a model. Must be a ollama available model",
    )

    args = parser.parse_args()

    asyncio.run(run(args))
