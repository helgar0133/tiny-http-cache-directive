"""tiny-http-cache-directive: parse an HTTP Cache-Control header.

Public API:
    parse_cache_control(header) -> dict[str, object]
"""

from tiny_http_cache_directive.core import parse_cache_control

__all__ = ["parse_cache_control"]
