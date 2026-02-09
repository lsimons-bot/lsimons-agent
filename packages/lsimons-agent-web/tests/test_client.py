"""Tests for client module."""

from lsimons_agent_web.client import format_args


def testformat_args_simple():
    """Test formatting simple arguments."""
    result = format_args({"path": "/foo/bar"})
    assert result == "path='/foo/bar'"


def testformat_args_truncates_long_strings():
    """Test that long strings are truncated."""
    long_string = "a" * 50
    result = format_args({"content": long_string})
    assert "..." in result
    assert len(result) < 60


def testformat_args_multiple():
    """Test formatting multiple arguments."""
    result = format_args({"a": "1", "b": "2"})
    assert "a='1'" in result
    assert "b='2'" in result
