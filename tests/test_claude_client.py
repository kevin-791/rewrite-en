from types import SimpleNamespace

import anthropic
try:
    import httpx2 as httpx
except ImportError:  # anthropic < 1.0
    import httpx
import pytest

from rewrite_en.claude_client import ClaudeRewriter, RewriteError, clean_output
from rewrite_en.config import default_config
from rewrite_en.prompts import SYSTEM_PROMPT


def block(text, type_="text"):
    return SimpleNamespace(type=type_, text=text)


class FakeMessages:
    def __init__(self, content=None, stop_reason="end_turn", error=None):
        self.content = content if content is not None else [block("Hello")]
        self.stop_reason = stop_reason
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.content, stop_reason=self.stop_reason)


def make(**kw):
    msgs = FakeMessages(**kw)
    client = SimpleNamespace(messages=msgs)
    return ClaudeRewriter(default_config("win32"), "sk-test", client=client), msgs


def test_request_shape():
    rw, msgs = make()
    assert rw.rewrite("xin chào") == "Hello"
    call = msgs.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert call["system"] == SYSTEM_PROMPT
    assert call["messages"] == [{"role": "user", "content": "<text>\nxin chào\n</text>"}]
    assert call["max_tokens"] == 2048
    assert "temperature" not in call  # rejected by current models


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('"Hello there."', "Hello there."),
        ("“Hello there.”", "Hello there."),
        ("```\nHello there.\n```", "Hello there."),
        ("```text\nline 1\nline 2\n```", "line 1\nline 2"),
        ("  Hello  \n", "Hello"),
        ('He said "hi" and "bye"', 'He said "hi" and "bye"'),
        ('"a" and "b"', '"a" and "b"'),
    ],
)
def test_clean_output(raw, expected):
    assert clean_output(raw, "original") == expected


def test_clean_output_keeps_quotes_when_original_was_quoted():
    assert clean_output('"Hello."', '"Xin chào."') == '"Hello."'


def test_clean_output_keeps_fence_when_original_was_fenced():
    assert clean_output("```\ncode\n```", "```\ncode\n```") == "```\ncode\n```"


def test_thinking_blocks_are_ignored():
    rw, _ = make(content=[block("", "thinking"), block("Hi")])
    assert rw.rewrite("chào") == "Hi"


def test_empty_result_is_error():
    rw, _ = make(content=[block('  ""  ')])
    with pytest.raises(RewriteError) as e:
        rw.rewrite("chào")
    assert e.value.code == "empty_output"


def test_too_long_does_not_call_api():
    rw, msgs = make()
    with pytest.raises(RewriteError) as e:
        rw.rewrite("a" * 6001)
    assert e.value.code == "too_long"
    assert msgs.calls == []


def test_refusal_and_truncation_are_errors():
    rw, _ = make(stop_reason="refusal")
    with pytest.raises(RewriteError, match="declined"):
        rw.rewrite("chào")
    rw, _ = make(stop_reason="max_tokens")
    with pytest.raises(RewriteError) as e:
        rw.rewrite("chào")
    assert e.value.code == "truncated"


def _status_error(cls, status):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(status, request=req)
    return cls("err", response=resp, body=None)


@pytest.mark.parametrize(
    "error,code",
    [
        (_status_error(anthropic.AuthenticationError, 401), "auth"),
        (_status_error(anthropic.RateLimitError, 429), "rate_limited"),
        (_status_error(anthropic.InternalServerError, 529), "http_529"),
        (anthropic.APIConnectionError(request=httpx.Request("POST", "https://x")), "network"),
        (anthropic.APITimeoutError(request=httpx.Request("POST", "https://x")), "timeout"),
    ],
)
def test_api_errors_map_to_codes(error, code):
    rw, _ = make(error=error)
    with pytest.raises(RewriteError) as e:
        rw.rewrite("chào")
    assert e.value.code == code
    # Error messages never contain the user's text.
    assert "chào" not in str(e.value)
