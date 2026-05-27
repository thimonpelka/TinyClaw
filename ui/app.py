import json
from argparse import Namespace
from pathlib import Path
from typing import override

from mcp import ClientSession
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, RichLog
from typing_extensions import final

from agent.agent import Agent
from config import ASCII_LOGO, MODEL, PROVIDER, SYSTEM_PROMPT
from custom_types import Mode, OllamaTool
from features.commands import CommandContext, CommandRegistry, register_all_commands
from features.skills import SkillsManager
from llm.llm import LLMClient
from ui.logging import write_assistant, write_error, write_system, write_user

SKILLS_DIR = Path(__file__).parent.parent / "skill-definitions"


@final
class ChatApp(App):
    """Textual chat UI for TinyClaw."""

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
    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(
        self,
        tool_registry: dict[str, ClientSession],
        tools: list[OllamaTool],
        args: Namespace,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        llm_client = LLMClient(
            provider=PROVIDER,
            model=MODEL,
            system_prompt=SYSTEM_PROMPT,
        )
        self.agent = Agent(
            llm_client=llm_client,
            tool_registry=tool_registry,
            tools=tools,
            debug=args.debug,
        )
        self.tools = tools
        self.mode = Mode.NORMAL
        self.debug_active = args.debug
        self.loading = False
        self.spinner_frame = 0
        self.spinner_task = None

        self.skills_manager = SkillsManager(SKILLS_DIR)
        self.registry = CommandRegistry()
        register_all_commands(self.registry)

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

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        self.query_one("#tools", RichLog).display = False
        self.query_one("#loadingStatus", Label).display = False

        self.skills_manager.load()
        self.query_one("#skillsStatus", Label).update(
            self.skills_manager.indicator_text()
        )

        write_system(log, ASCII_LOGO)
        if self.debug_active:
            write_system(log, "Debug mode is active. Expect detailed logs.")

        tool_names = [tool["function"]["name"] for tool in self.tools]
        if tool_names:
            write_system(log, f"Successfully loaded tools: {', '.join(tool_names)}")
        else:
            write_system(log, "No tools loaded (add .py files to plugins/)")

        skill_count = len(self.skills_manager.skills)
        if skill_count:
            write_system(log, f"Loaded {skill_count} skill(s). Press 's' to browse.")
        else:
            write_system(log, "No skills loaded (add .md files to skill-definitions/)")

        write_system(log, f"{self.TITLE} is ready for you! Press 'i' to interact.")
        self._update_status()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.mode != Mode.INSERT:
            return

        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        log = self.query_one("#log", RichLog)

        if text.startswith("/"):
            ctx = CommandContext(
                log=log,
                write_system=lambda t: write_system(log, t),
                write_error=lambda t: write_error(log, t),
                send_message=lambda display, full: self._send_message(display, full, log),
                update_indicator=self._update_skills_indicator,
                skills=self.skills_manager,
            )
            handled = await self.registry.dispatch(text[1:], ctx)
            if not handled:
                write_error(log, f"Unknown command: {text}")
            return

        prefix = self.skills_manager.build_prefix()
        full_text = f"{prefix}\n\n---\n\n{text}" if prefix else text
        self._send_message(text, full_text, log)

    def _send_message(self, display_text: str, full_text: str, log: RichLog) -> None:
        write_user(log, display_text)
        self.run_worker(
            self._agent_turn(full_text, log),
            exclusive=True,
            thread=False,
        )

    def _update_skills_indicator(self) -> None:
        self.query_one("#skillsStatus", Label).update(
            self.skills_manager.indicator_text()
        )

    def action_enter_insert(self) -> None:
        self.mode = Mode.INSERT
        self._show_chat_log()

        input_field = self.query_one(Input)
        input_field.disabled = False
        input_field.focus()
        input_field.placeholder = "Type a message..."
        self._update_status()

    def action_enter_normal(self) -> None:
        self.mode = Mode.NORMAL
        self._show_chat_log()

        input_field = self.query_one(Input)
        input_field.disabled = True
        input_field.blur()
        self._update_status()

    def action_show_tools(self) -> None:
        self.mode = Mode.TOOLS
        tools_view = self.query_one("#tools", RichLog)
        self.query_one("#log", RichLog).display = False
        tools_view.display = True
        tools_view.clear()

        for tool in self.tools:
            function = tool["function"]
            tools_view.write(f"[bold #bb9af7]{function['name']}[/]")
            write_system(tools_view, function["description"])
            write_system(tools_view, json.dumps(function["parameters"], indent=2))

        self._update_status()

    def action_show_skills(self) -> None:
        log = self.query_one("#log", RichLog)
        self._show_chat_log()

        if not self.skills_manager.skills:
            write_system(log, "No skills loaded (add .md files to skill-definitions/)")
            return

        write_system(log, "Available skills (● = active):")
        for badge, desc, when in self.skills_manager.list_renderables():
            log.write(f"  {badge} — {desc}  [dim](use when: {when})[/dim]")

    def action_clear_chat(self) -> None:
        self.agent.clear_history()
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

    async def _agent_turn(self, user_message: str, log: RichLog) -> None:
        self.action_enter_normal()
        self._start_loading()

        async def log_callback(role: str, text: str) -> None:
            if not text:
                return
            if role == "assistant":
                write_assistant(log, text)
            elif role == "user":
                write_user(log, text)
            else:
                write_system(log, text)

        await self.agent.turn(user_message, log_callback)
        self._stop_loading()

    def _show_chat_log(self) -> None:
        self.query_one("#tools", RichLog).display = False
        self.query_one("#log", RichLog).display = True

    def _update_status(self) -> None:
        labels = {
            Mode.NORMAL: "[bold yellow]NORMAL[/]",
            Mode.INSERT: "[bold green]INSERT[/]",
            Mode.TOOLS: "[bold magenta]TOOLS[/]",
        }
        self.query_one("#status", Label).update(labels[self.mode])

    def _start_loading(self) -> None:
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

    def _stop_loading(self) -> None:
        self.loading = False
        if self.spinner_task:
            self.spinner_task.stop()
            self.query_one("#loadingStatus", Label).display = False
            self.spinner_task = None
        self._update_status()
