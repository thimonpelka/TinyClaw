import asyncio
import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import override

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Label
from typing_extensions import final

from custom_types import CommandHistory, LLMTool, Mode
from features.commands import CommandContext, CommandRegistry, register_all_commands
from features.skills import SkillsManager
from llm import LLMMessage, get_provider, load_config, resolve_model
from llm.protocol import LLMProvider, ToolCall

SERVER_SCRIPT = Path(__file__).parent / "mcp_server.py"
SKILLS_DIR = Path(__file__).parent / "skill-definitions"
MAX_STEPS = 8
MAX_HISTORY = 20

ASCII_LOGO = """
████████╗██╗███╗   ██╗██╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
╚══██╔══╝██║████╗  ██║╚██╗ ██╔╝██╔════╝██║     ██╔══██╗██║    ██║
   ██║   ██║██╔██╗ ██║ ╚████╔╝ ██║     ██║     ███████║██║ █╗ ██║
   ██║   ██║██║╚██╗██║  ╚██╔╝  ██║     ██║     ██╔══██║██║███╗██║
   ██║   ██║██║ ╚████║   ██║   ╚██████╗███████╗██║  ██║╚███╔███╔╝
   ╚═╝   ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
"""


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

    mode: Mode
    debug_active: bool
    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    tool_names: list[str] = []
    provider_ready: bool = False

    def __init__(
        self,
        session: ClientSession,
        tools: list[LLMTool],
        provider: LLMProvider,
        model: str,
        debug: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.session = session
        self.tools = tools
        self.tool_names = [tool["function"]["name"] for tool in tools]
        self.history: list[dict] = []
        self.mode = Mode.NORMAL
        self.debug_active = debug
        self.model = model
        self.provider = provider

        self.skills_manager = SkillsManager(SKILLS_DIR)
        self.registry = CommandRegistry()
        register_all_commands(self.registry)

        self.loading = False
        self.spinner_frame = 0
        self.spinner_task = None

    def write_user(self, log: RichLog, text: str) -> None:
        log.write("\n[bold #7aa2f7]You[/bold #7aa2f7]")
        log.write(f"[#c0caf5]{text}[/]\n")
        log.scroll_end(animate=False)

    def write_system(self, log: RichLog, text: str) -> None:
        log.write(f"[dim]{text}[/dim]\n")
        log.scroll_end(animate=False)

    def write_error(self, log: RichLog, text: str) -> None:
        log.write(f"[bold #8B0000]{text}[/bold #8B0000]\n")
        log.scroll_end(animate=False)

    def write_assistant(self, log: RichLog, text: str) -> None:
        log.write(f"\n[bold #9ece6a]{self.TITLE}[/bold #9ece6a]")
        log.write(f"[#c0caf5]{text}[/]\n")
        log.scroll_end(animate=False)

    @override
    def compose(self) -> ComposeResult:
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

    def update_status(self) -> None:
        status = self.query_one("#status", Label)
        if self.mode == Mode.NORMAL:
            status.update("[bold yellow]NORMAL[/]")
        elif self.mode == Mode.INSERT:
            status.update("[bold green]INSERT[/]")
        elif self.mode == Mode.TOOLS:
            status.update("[bold magenta]TOOLS[/]")

    def add_to_history(self, new_item: dict) -> None:
        self.history.append(new_item)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

    async def on_unmount(self) -> None:
        self.provider.shutdown()

    async def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)

        tool_names = [t["function"]["name"] for t in self.tools] if self.tools else []

        tools_view = self.query_one("#tools", RichLog)
        tools_view.display = False

        loading_label = self.query_one("#loadingStatus", Label)
        loading_label.display = False

        self.skills_manager.load()
        self.query_one("#skillsStatus", Label).update(
            self.skills_manager.indicator_text()
        )

        self.write_system(log, ASCII_LOGO)

        if self.debug_active:
            self.write_system(log, "Debug mode is active. Expect detailed logs.")

        if tool_names:
            self.write_system(log, f"Succesfully loaded tools: {', '.join(tool_names)}")
        else:
            self.write_system(log, "No tools loaded (add .py files to plugins/)")

        skill_count = len(self.skills_manager.skills)
        if skill_count:
            self.write_system(
                log, f"Loaded {skill_count} skill(s). Press 's' to browse."
            )
        else:
            self.write_system(
                log, "No skills loaded (add .md files to skill-definitions/)"
            )

        self.update_status()

        self.run_worker(
            self._ensure_readiness(log),
            exclusive=True,
            thread=False,
        )

    async def _ensure_readiness(self, log: RichLog) -> None:
        loading_label = self.query_one("#loadingStatus", Label)

        def on_progress(msg: str) -> None:
            if msg:
                loading_label.display = True
                loading_label.update(msg)
            else:
                loading_label.display = False

        try:
            self.write_system(log, f"Preparing provider (model: {self.model})...")
            await self.provider.ensure_ready(
                self.model,
                on_log=lambda msg: self.write_system(log, msg),
                on_progress=on_progress,
            )
            loading_label.display = False
            self.provider_ready = True
            self.write_system(
                log, f"{self.TITLE} is ready for you! Press 'i' to interact."
            )
        except Exception as e:
            loading_label.display = False
            self.write_error(log, f"Provider setup failed: {e}")

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
        if self.mode != Mode.INSERT:
            return

        log = self.query_one("#log", RichLog)

        if not self.provider_ready:
            self.write_system(log, "Provider is not yet ready. Please wait...")
            return

        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/"):
            ctx = CommandContext(
                log=log,
                write_system=lambda t: self.write_system(log, t),
                write_error=lambda t: self.write_error(log, t),
                send_message=lambda display, full: self._send_message(
                    display, full, log
                ),
                update_indicator=self._update_skills_indicator,
                skills=self.skills_manager,
                extras={"app": self},
            )
            handled = await self.registry.dispatch(text[1:], ctx)
            if not handled:
                self.write_error(log, f"Unknown command: {text}")
            return

        prefix = self.skills_manager.build_prefix()
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

    def _update_skills_indicator(self) -> None:
        label = self.query_one("#skillsStatus", Label)
        label.update(self.skills_manager.indicator_text())

    def action_enter_insert(self) -> None:
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
        if not self.skills_manager.skills:
            self.write_system(
                log, "No skills loaded (add .md files to skill-definitions/)"
            )
            return
        self.write_system(log, "Available skills (● = active):")
        for badge, desc, when in self.skills_manager.list_renderables():
            log.write(f"  {badge} — {desc}  [dim](use when: {when})[/dim]")

    def action_clear_chat(self) -> None:
        self.history.clear()
        self.query_one("#log", RichLog).clear()

    def action_scroll_up(self) -> None:
        if self.mode == Mode.NORMAL:
            self.query_one("#log").scroll_up()
        elif self.mode == Mode.TOOLS:
            self.query_one("#tools").scroll_up()

    def action_scroll_down(self) -> None:
        if self.mode == Mode.NORMAL:
            self.query_one("#log").scroll_down()
        elif self.mode == Mode.TOOLS:
            self.query_one("#tools").scroll_down()

    async def _agent_turn(self, log: RichLog) -> None:
        """Agentic loop: call provider, handle tool calls, repeat."""
        self.action_enter_normal()
        self.start_loading()

        if self.debug_active:
            self.write_system(log, "Starting communication with Agent.")

        for step in range(MAX_STEPS):
            if self.debug_active:
                self.write_system(log, f"Communication iteration {step} with Agent")

            msg = await self.provider.chat(
                messages=[
                    {"role": "system", "content": self.skills_manager.system_prompt()}
                ]
                + self.history,
                tools=self.tools,
                model=self.model,
            )

            if self.debug_active:
                self.write_system(log, str(msg))

            self.add_to_history(msg.history_entry)

            if msg.content:
                self.write_assistant(log, msg.content)

            if not msg.tool_calls:
                break

            tasks = [self._execute_tool(call, log) for call in msg.tool_calls]
            results = await asyncio.gather(*tasks)
            for res in results:
                self.add_to_history(res)

            self.write_system(log, "All tool calls completed")

            if self.debug_active and step == (MAX_STEPS - 1):
                self.write_system(log, "Max steps reached. Stopping.")

        self.stop_loading()

    async def _execute_tool(self, call: ToolCall, log: RichLog) -> dict:
        """Executes a tool call requested by the LLM."""
        name = call.name
        args = call.arguments

        if name not in self.tool_names:
            return self.provider.make_tool_result(
                call, f"Error: Tool '{name}' does not exist"
            )

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

            return self.provider.make_tool_result(call, result_text)

        except Exception as e:
            self.write_system(log, f"{name} failed: {e}")
            return self.provider.make_tool_result(call, f"Error: {e}")


async def run(args: Namespace) -> None:
    load_dotenv()

    config = load_config()
    provider_name: str = config.get("provider", "ollama")
    provider = get_provider(provider_name)
    model = resolve_model(config, provider_name, args.model)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            llm_tools: list[LLMTool] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema,
                    },
                }
                for t in tools_response.tools
            ]

            app = ChatApp(
                session=session,
                tools=llm_tools,
                provider=provider,
                model=model,
                debug=args.debug,
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
        help="Override the model defined in config.toml for this session.",
    )

    args = parser.parse_args()
    asyncio.run(run(args))
