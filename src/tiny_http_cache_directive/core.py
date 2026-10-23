"""Parser for the HTTP/1.1 Cache-Control header.

The header has a small grammar (RFC 7234 §5.2) but real-world senders are
sloppy. Two design decisions are worth calling out:

* The return type mixes ints, strings, and bools. Bools are used for bare
  directive names without a value (``public``, ``no-store``). Ints are used
  for the known delta-seconds directives (``max-age`` and ``s-maxage``).
  Any other directive with a value keeps that value as a string, because
  the spec allows arbitrary tokens and trying to coerce them loses
  information a caller might need.

* Duplicate directive names are kept in insertion order by appending an
  underscore index to the key. RFC 7234 says a directive is identified by
  its name and any argument, and that a given directive-name should appear
  at most once; it does not say what a recipient does when it appears more
  than once. Rather than silently drop or silently overwrite, we preserve
  every value under a distinct, predictable key. A caller who knows the
  header well can ignore the suffixed keys; one debugging a misbehaving
  origin still sees what was actually sent.
"""

from __future__ import annotations

__all__ = ["parse_cache_control"]

# These directives are defined in RFC 7234 to take a delta-seconds argument.
# We parse their values as int so callers do not have to re-coerce them.
_INT_DIRECTIVES = {"max-age", "s-maxage"}


def _split_directives(header: str) -> list[str]:
    """Split a Cache-Control header into raw directive strings.

    Commas inside a quoted-string are part of the quoted value, not a
    directive boundary, so we cannot naively split on commas. We walk the
    string with a small state machine that treats a double quote as a toggle.
    """
    parts: list[str] = []
    current: list[str] = []
    in_quotes = False
    for ch in header:
        if ch == '"':
            in_quotes = not in_quotes
            current.append(ch)
        elif ch == "," and not in_quotes:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return parts


def _parse_delta(value: str) -> int | str:
    """Try to read a delta-seconds value; fall back to the raw string.

    Non-negative decimal integers are returned as int. Anything else (e.g.
    ``"100"`` the quoted string, or ``0x10``) is returned unchanged so the
    caller can see what was actually sent rather than a guessed coercion.
    """
    if value.isdigit():
        return int(value)
    return value


def parse_cache_control(header: str) -> dict[str, object]:
    """Parse a Cache-Control header into a dict of directives.

    >>> parse_cache_control("public, max-age=600")
    {'public': True, 'max-age': 600}

    Bare directives map to ``True``. Delta-seconds directives (``max-age``,
    ``s-maxage``) map to ``int`` when the value is a non-negative decimal.
    Other directives keep their raw value as ``str``. Duplicate directive
    names are preserved under keys of the form ``"name_2"``, ``"name_3"``,
    ... in the order they appear.

    An empty or whitespace-only header returns an empty dict.
    """
    result: dict[str, object] = {}

    if header is None:
        return result

    for raw in _split_directives(header):
        text = raw.strip()
        if not text:
            continue

        # Split on the first "=". Everything after is the argument, which
        # may itself contain "=" (inside a quoted string, for example).
        if "=" in text:
            name_part, _, value_part = text.partition("=")
            name = name_part.strip().lower()
            value = value_part.strip()
            # Strip one layer of surrounding double quotes, matching the
            # common form ``max-age="100"``. We do NOT collapse escaped
            # sequences; that is left to the caller's needs.
            if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            if name in _INT_DIRECTIVES:
                value = _parse_delta(value)
        else:
            name = text.lower()
            value = True

        if name in result:
            # Preserve duplicates under a predictable suffix. The first
            # occurrence is unchanged so callers who do not expect
            # duplicates can keep working with the familiar key.
            i = 2
            while f"{name}_{i}" in result:
                i += 1
            key = f"{name}_{i}"
        else:
            key = name

        result[key] = value

    return result
