"""
Plugin: time
Gets the current time
"""

import datetime


@mcp.tool()
def get_time() -> str:
    "Get the current system time"
    return str(datetime.datetime.now())
