import json
from pathlib import Path

from main import load_mcp_config


def test_load_mcp_config_missing_file(tmp_path):
    result = load_mcp_config(tmp_path / "mcp.json")
    assert result == {"mcpServers": {}}


def test_load_mcp_config_parses_servers(tmp_path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text(json.dumps({
        "mcpServers": {
            "discord": {
                "command": "uvx",
                "args": ["mcp-server-discord"],
                "env": {"DISCORD_TOKEN": "placeholder"}
            }
        }
    }))
    result = load_mcp_config(config_path)
    assert "discord" in result["mcpServers"]
    assert result["mcpServers"]["discord"]["command"] == "uvx"
    assert result["mcpServers"]["discord"]["args"] == ["mcp-server-discord"]


def test_load_mcp_config_no_mcpservers_key(tmp_path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text(json.dumps({"tinyclaw": {"token_ttl": {}}}))
    result = load_mcp_config(config_path)
    assert result.get("mcpServers", {}) == {}
