from typing import TypedDict
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
