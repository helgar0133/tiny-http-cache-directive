"""Tests for tiny_http_cache_directive.core.parse_cache_control.

These tests exercise the behaviour the implementation actually claims to
support: bare directives, valued directives, delta-seconds coercion for the
two known int directives, quoted-string handling, duplicate handling, and
the empty header. They deliberately avoid inventing richer semantics (such
as merging duplicate max-age values) that the parser does not implement.
"""

import unittest

from tiny_http_cache_directive import parse_cache_control


class ParseCacheControlTests(unittest.TestCase):

    def test_empty_header_returns_empty_dict(self):
        self.assertEqual(parse_cache_control(""), {})

    def test_whitespace_only_header_returns_empty_dict(self):
        self.assertEqual(parse_cache_control("   \t "), {})

    def test_none_header_returns_empty_dict(self):
        self.assertEqual(parse_cache_control(None), {})

    def test_bare_directive_maps_to_true(self):
        result = parse_cache_control("no-store")
        self.assertEqual(result, {"no-store": True})

    def test_multiple_bare_directives(self):
        result = parse_cache_control("public, no-cache, no-store")
        self.assertEqual(
            result,
            {"public": True, "no-cache": True, "no-store": True},
        )

    def test_directive_names_are_lowercased(self):
        result = parse_cache_control("PUBLIC, Max-Age=300")
        self.assertEqual(result, {"public": True, "max-age": 300})

    def test_max_age_integer_value(self):
        result = parse_cache_control("max-age=600")
        self.assertEqual(result, {"max-age": 600})
        self.assertIsInstance(result["max-age"], int)

    def test_s_maxage_integer_value(self):
        result = parse_cache_control("s-maxage=60")
        self.assertEqual(result, {"s-maxage": 60})
        self.assertIsInstance(result["s-maxage"], int)

    def test_max_age_zero(self):
        # A directive that says "not cacheable" should still be an int 0,
        # not a falsy bool or missing key.
        result = parse_cache_control("max-age=0")
        self.assertEqual(result, {"max-age": 0})
        self.assertIsInstance(result["max-age"], int)

    def test_unknown_directive_keeps_string_value(self):
        result = parse_cache_control("stale-while-revalidate=120")
        self.assertEqual(result, {"stale-while-revalidate": "120"})
        self.assertIsInstance(result["stale-while-revalidate"], str)

    def test_directive_with_quoted_value_unquoted(self):
        result = parse_cache_control('no-cache="Set-Cookie, Vary"')
        self.assertEqual(result, {"no-cache": "Set-Cookie, Vary"})

    def test_comma_inside_quoted_string_is_not_a_separator(self):
        result = parse_cache_control('no-cache="a, b", public')
        self.assertEqual(result, {"no-cache": "a, b", "public": True})

    def test_whitespace_around_directive_name_is_stripped(self):
        result = parse_cache_control("  public  ,  max-age =  10  ")
        self.assertEqual(result, {"public": True, "max-age": 10})

    def test_non_decimal_max_age_kept_as_string(self):
        # The parser only coerces non-negative decimal integers to int.
        # A hex-looking value or anything non-digit stays a string so the
        # caller can decide what to do.
        result = parse_cache_control("max-age=0x10")
        self.assertEqual(result, {"max-age": "0x10"})
        self.assertIsInstance(result["max-age"], str)

    def test_duplicate_directives_get_suffixed_keys(self):
        result = parse_cache_control("max-age=10, max-age=20")
        self.assertEqual(result, {"max-age": 10, "max-age_2": 20})

    def test_duplicate_directive_with_three_occurrences(self):
        result = parse_cache_control("public, public, public")
        self.assertEqual(
            result,
            {"public": True, "public_2": True, "public_3": True},
        )

    def test_duplicate_directives_preserve_order(self):
        result = parse_cache_control(
            "no-cache, no-cache, public, no-cache"
        )
        self.assertEqual(
            result,
            {
                "no-cache": True,
                "no-cache_2": True,
                "public": True,
                "no-cache_3": True,
            },
        )
        # Order must reflect the header, not the key names.
        self.assertEqual(
            list(result.keys()),
            ["no-cache", "no-cache_2", "public", "no-cache_3"],
        )

    def test_value_containing_equals_sign(self):
        # partition() splits on the first "=" only, so the argument can
        # itself contain "=".
        result = parse_cache_control('community="UCI=lua"')
        self.assertEqual(result, {"community": "UCI=lua"})

    def test_bare_directive_with_trailing_equals_sign(self):
        # "foo=" yields an empty-string value, not a bool. This is the
        # honest interpretation of what the bytes say.
        result = parse_cache_control("foo=")
        self.assertEqual(result, {"foo": ""})

    def test_mixed_realistic_header(self):
        result = parse_cache_control(
            'public, max-age=3600, s-maxage=600, no-cache="Set-Cookie", '
            'stale-while-revalidate=120'
        )
        self.assertEqual(
            result,
            {
                "public": True,
                "max-age": 3600,
                "s-maxage": 600,
                "no-cache": "Set-Cookie",
                "stale-while-revalidate": "120",
            },
        )


if __name__ == "__main__":
    unittest.main()
