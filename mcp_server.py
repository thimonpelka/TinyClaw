import importlib.util
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-tools")

PLUGINS_DIR = Path(__file__).parent / "plugins"

# MCP Server
# Auto-loads plugins from /plugins directory
# Each file is supposed to be one self-contained tool definition


def load_plugins():
    """Dynamically load and register all plugins from the plugins directory."""

    if not PLUGINS_DIR.exists():
        print("[mcp_server] plugins/ directory not found, creating it.", file=sys.stderr)
        PLUGINS_DIR.mkdir()
        return

    for plugin_file in sorted(PLUGINS_DIR.glob("*.py")):
        if plugin_file.name.startswith("_"):
            continue  # skip __init__.py etc.

        module_name = f"plugins.{plugin_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)

        if spec is None:
            print(f"[mcp_server] Could not load spec from file. Skipping plugin \"{plugin_file}\".", file=sys.stderr)
            break

        module = importlib.util.module_from_spec(spec)

        # Inject the mcp instance so plugins can register tools
        module.mcp = mcp  # pyright: ignore[reportAttributeAccessIssue]

        try:
            if spec.loader is None:
                print(f"[mcp_server] Loader of spec is null. Skipping plugin \"{plugin_file}\".", file=sys.stderr)
                break

            spec.loader.exec_module(module)
            print(f"[mcp_server] Loaded plugin: {plugin_file.name}", file=sys.stderr)
        except Exception as e:
            print(f"[mcp_server] Failed to load {plugin_file.name}: {e}", file=sys.stderr)


load_plugins()

if __name__ == "__main__":
    mcp.run()
