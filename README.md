# tiny-http-cache-directive

Parse an HTTP `Cache-Control` header into a `dict` of directives with their parameters.

```python
from tiny_http_cache_directive import parse_cache_control

result = parse_cache_control('public, max-age=600, no-cache="Set-Cookie"')
# {'public': True, 'max-age': 600, 'no-cache': 'Set-Cookie'}
```

## Why

The standard library does not ship a `Cache-Control` parser and most call
sites hand-roll a `.split(",")` that breaks the moment a value is a
quoted-string containing a comma. This library exists to do that one job
well, with no dependencies.

The return type is mixed on purpose: bare directives map to `bool`,
`max-age` and `s-maxage` map to `int` when their value is a non-negative
decimal, and everything else keeps a `str` value. This matches what the
spec defines and avoids guessing coercions for unknown directives.

## Edge you will hit

RFC 7234 does not say what a recipient should do when a directive appears
more than once. Rather than silently drop or overwrite, this parser
preserves every value: the first occurrence keeps the plain name and
subsequent ones get a predictable `"name_2"`, `"name_3"` suffix. If your
upstream sends a single, well-formed directive you will never see these; if
it does not, you at least see what was actually sent.
