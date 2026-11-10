"""Call Claude to rewrite text, and clean up the result."""

from __future__ import annotations

import logging
import re
import time

import anthropic

from rewrite_en.config import Config
from rewrite_en.prompts import SYSTEM_PROMPT, build_user_message

log = logging.getLogger(__name__)


class RewriteError(RuntimeError):
    """Any failure that should leave the user's text untouched.

    `code` is a short machine-readable reason, safe to log (never contains text).
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


_FENCE_RE = re.compile(r"^```[\w-]*\n(.*?)\n?```$", re.DOTALL)
_QUOTE_PAIRS = [('"', '"'), ("“", "”"), ("'", "'")]


def clean_output(raw: str, original: str = "") -> str:
    """Strip whitespace, a wrapping code fence, or wrapping quotes.

    Quotes or fences are only removed when the original text was not itself
    wrapped that way.
    """
    text = raw.strip()
    orig = original.strip()
    m = _FENCE_RE.match(text)
    if m and not orig.startswith("```"):
        text = m.group(1).strip()
    for left, right in _QUOTE_PAIRS:
        if (
            len(text) >= 2
            and text.startswith(left)
            and text.endswith(right)
            and not (orig.startswith(left) and orig.endswith(right))
            # Don't strip if the quote char also appears inside (e.g. "a" and "b").
            and left not in text[1:-1]
            and right not in text[1:-1]
        ):
            text = text[1:-1].strip()
            break
    return text


class ClaudeRewriter:
    def __init__(self, config: Config, api_key: str, client: anthropic.Anthropic | None = None):
        self.config = config
        self.client = client or anthropic.Anthropic(
            api_key=api_key,
            timeout=config.timeout_seconds,
            max_retries=1,
        )

    def rewrite(self, text: str) -> str:
        if not text.strip():
            raise RewriteError("empty_input", "Nothing to rewrite")
        if len(text) > self.config.max_chars:
            raise RewriteError(
                "too_long",
                f"Selection is {len(text)} characters; the limit is {self.config.max_chars}",
            )

        started = time.monotonic()
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_message(text)}],
                output_config={"effort": self.config.effort},
            )
        except anthropic.AuthenticationError as e:
            raise RewriteError("auth", "API key was rejected (401)") from e
        except anthropic.PermissionDeniedError as e:
            raise RewriteError("permission", "API key lacks permission (403)") from e
        except anthropic.NotFoundError as e:
            raise RewriteError("model_not_found", f"Model {self.config.model!r} not found") from e
        except anthropic.RateLimitError as e:
            raise RewriteError("rate_limited", "Rate limited (429)") from e
        except anthropic.BadRequestError as e:
            raise RewriteError("bad_request", "Request rejected (400)") from e
        except anthropic.APIStatusError as e:
            raise RewriteError(f"http_{e.status_code}", f"API error {e.status_code}") from e
        except anthropic.APITimeoutError as e:
            raise RewriteError("timeout", "Request timed out") from e
        except anthropic.APIConnectionError as e:
            raise RewriteError("network", "Could not reach the API") from e

        elapsed = time.monotonic() - started
        if response.stop_reason == "refusal":
            raise RewriteError("refusal", "The model declined to rewrite this text")
        if response.stop_reason == "max_tokens":
            raise RewriteError("truncated", "Output hit max_tokens; not pasting a partial rewrite")

        # Responses may include thinking blocks; only text blocks are the answer.
        raw = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        result = clean_output(raw, text)
        if not result:
            raise RewriteError("empty_output", "Model returned an empty result")
        log.info(
            "rewrite ok: in_chars=%d out_chars=%d api_seconds=%.2f",
            len(text), len(result), elapsed,
        )
        return result
