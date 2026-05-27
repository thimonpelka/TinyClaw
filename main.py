import asyncio
from argparse import ArgumentParser, Namespace
from contextlib import AsyncExitStack
from pathlib import Path

from mcp_client import connect_mcp_servers, load_mcp_config
from ui import ChatApp

_MEMORY_DIR = Path(".memory")
_MEMORY_OVERVIEW = _MEMORY_DIR / "memory_overview.md"


async def run(args: Namespace) -> None:
    """Connect MCP servers and start the TinyClaw TUI."""
    if not _MEMORY_DIR.exists():
        _MEMORY_DIR.mkdir()
        _MEMORY_OVERVIEW.write_text(
            "# Memory Overview\n\nNo memories saved yet.\n",
            encoding="utf-8",
        )

    async with AsyncExitStack() as stack:
        registry = await connect_mcp_servers(load_mcp_config(), stack)
        app = ChatApp(
            tool_registry=registry.sessions_by_tool,
            tools=registry.tools,
            args=args,
        )
        await app.run_async()


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="Print additional information to the log.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
