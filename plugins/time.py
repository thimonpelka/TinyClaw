"""
Plugin: time
Gets the current time
"""

import datetime

from mcp_server import mcp


@mcp.tool()
def get_time() -> str:
    """
    Get the current system time and date (datetime) in isoformat

    Use this when:
    - user asks for time/date
    - user says "now", "current", "today"

    Returns:
    - string timestamp in isoformat
    """
    return str(datetime.datetime.now().isoformat())


@mcp.tool()
def get_year() -> str:
    """
    Get the current system year

    Use this when:
    - user asks for month

    Returns:
    - string month
    """
    return str(datetime.datetime.now().year)


@mcp.tool()
def get_month() -> str:
    """
    Get the current system month. This must always be called after getting the year. Calling it before will break things

    Use this when:
    - user asks for month

    Returns:
    - string month
    """
    return str(datetime.datetime.now().month)


@mcp.tool()
def get_day() -> str:
    """
    Get the current system day

    Use this when:
    - user asks for day

    Returns:
    - string day
    """
    return str(datetime.datetime.now().day)


@mcp.tool()
def get_hour() -> str:
    """
    Get the current system hour

    Use this when:
    - user asks for hour

    Returns:
    - string hour
    """
    return str(datetime.datetime.now().hour)
