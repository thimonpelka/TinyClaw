from typing import Any, NotRequired, TypedDict
from enum import Enum


class FunctionSpec(TypedDict):
    name: str
    description: str
    parameters: dict[str, str]


class OllamaTool(TypedDict):
    type: str
    function: FunctionSpec


class CommandHistory(TypedDict):
    role: str
    content: str


class Mode(str, Enum):
    NORMAL = "normal"
    INSERT = "insert"
    TOOLS = "tools"


class McpServiceConfig(TypedDict):
    command: str
    args: list[str]
    env: NotRequired[dict[str, str]]


class McpConfig(TypedDict):
    mcpServers: dict[str, McpServiceConfig]
    tinyclaw: NotRequired[dict[str, Any]]
