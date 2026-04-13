"""
Plugin: time
Gets the current time
"""

import datetime


@mcp.tool()
def get_time() -> str:
    """
    "Get the current system time"

    Use this when:
    - user asks for time/date
    - user says "now", "current", "today"

    Returns:
    - string timestamp
    """
    return str(datetime.datetime.now())
