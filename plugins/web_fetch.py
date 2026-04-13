"""
Plugin: web_fetch
Fetches the text content of a URL.
"""
import urllib.request


@mcp.tool()
def web_fetch(url: str) -> str:
    """Fetch the content of a URL and return it as text (first 5000 chars)."""
    response = urllib.request.urlopen(url)
    return response.read().decode("utf-8")[:5000]
