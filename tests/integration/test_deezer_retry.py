"""Integration test for snippet-fetch retry logic.

Verifies that `genreguru.deezer.snippets` retries QUOTA (4) / SERVICE_BUSY
(700) error codes and network timeouts up to its `_MAX_RETRIES`-attempt
budget, succeeds when a later attempt succeeds, and raises
`NetworkDisconnectedError` immediately for non-retryable Deezer error codes,
`ConnectError`/`ReadError`, and non-200 statuses without an audio payload.

Tests fake the client's `httpx.get` with the shared `tests.http_stubs`
helpers. A `sequence` responder feeds events one per call: `httpx.Response`
items are returned, `Exception` items are raised (see
`tests.http_stubs.sequence`).
"""

import httpx
import pytest

from genreguru.deezer import snippets
from genreguru.errors import NetworkDisconnectedError
from tests.http_stubs import (
    RETRYABLE_CODES,
    audio,
    capture_get,
    error_envelope,
    repeat,
    response,
    retry_then_success,
    sequence,
)

_PREVIEW_URL = (
    "https://cdnt-preview.dzcdn.net/api/1/1/abc/def/0/abc.mp3"
    "?hdnea=exp=123~acl=/api*~data=user_id=0~hmac=abc"
)

_FAKE_AUDIO = b"\x00" * 1024

_MAX_RETRIES = snippets._MAX_RETRIES  # single source of truth

assert RETRYABLE_CODES == (4, 700)  # QUOTA, SERVICE_BUSY — guard against silent drift

_SNIPPETS_HTTP_GET = "genreguru.deezer.snippets.httpx.get"


def _fetch_ok(monkeypatch, responder) -> tuple[list[tuple[tuple, dict]], bytes]:
    """Patch `httpx.get`, dispatch `fetch_snippet`, return (calls, audio_bytes)."""
    calls = capture_get(monkeypatch, _SNIPPETS_HTTP_GET, responder)
    return calls, snippets.fetch_snippet(_PREVIEW_URL)


def _fetch_err(
    monkeypatch, responder
) -> tuple[list[tuple[tuple, dict]], NetworkDisconnectedError]:
    """Patch `httpx.get`, dispatch `fetch_snippet`, return (calls, error)."""
    calls = capture_get(monkeypatch, _SNIPPETS_HTTP_GET, responder)
    with pytest.raises(NetworkDisconnectedError) as exc_info:
        snippets.fetch_snippet(_PREVIEW_URL)
    return calls, exc_info.value


class TestHappyPath:
    """Verify the single-call success path without retries."""

    def test_first_attempt_succeeds(self, monkeypatch):
        """A successful first fetch must return audio after a single call."""
        calls, result = _fetch_ok(monkeypatch, audio(_FAKE_AUDIO, _PREVIEW_URL))
        assert result == _FAKE_AUDIO
        assert len(calls) == 1


class TestRetryableFailures:
    """Failures that trigger a retry, succeeding on the final attempt."""

    @pytest.mark.parametrize("code", RETRYABLE_CODES)
    def test_retryable_error_code_then_success(self, monkeypatch, code):
        """A retryable Deezer error code must be retried, succeeding on the last attempt."""
        error = error_envelope(200, code, _PREVIEW_URL)
        calls, result = _fetch_ok(
            monkeypatch,
            retry_then_success(
                error, audio(_FAKE_AUDIO, _PREVIEW_URL), _MAX_RETRIES - 1
            ),
        )
        assert result == _FAKE_AUDIO
        assert len(calls) == _MAX_RETRIES

    def test_retryable_error_code_exhausts_budget(self, monkeypatch):
        """Repeated retryable codes exhaust the budget, raising the code.

        One representative code suffices: proving each code retryable belongs to
        `test_retryable_error_code_then_success` (parametrized over all); this covers
        exhaustion + code propagation. A second code here would duplicate, not extend.
        """
        error = error_envelope(200, RETRYABLE_CODES[0], _PREVIEW_URL)
        _, exc = _fetch_err(monkeypatch, repeat(error, _MAX_RETRIES))
        assert exc.attempts == _MAX_RETRIES
        assert exc.code == RETRYABLE_CODES[0]

    @pytest.mark.parametrize(
        "timeout",
        [
            httpx.ConnectTimeout("connection timed out"),
            httpx.ReadTimeout("read timed out"),
        ],
        ids=["connect_timeout", "read_timeout"],
    )
    def test_network_timeout_retries_then_success(self, monkeypatch, timeout):
        """A ConnectTimeout/ReadTimeout must be retried, succeeding on the last attempt."""
        calls, result = _fetch_ok(
            monkeypatch,
            retry_then_success(
                timeout, audio(_FAKE_AUDIO, _PREVIEW_URL), _MAX_RETRIES - 1
            ),
        )
        assert result == _FAKE_AUDIO
        assert len(calls) == _MAX_RETRIES


class TestNonRetryableFailures:
    """Failures that raise immediately without retrying."""

    @pytest.mark.parametrize(
        "exc",
        [
            httpx.ConnectError("DNS resolution failed"),
            httpx.ReadError("stream interrupted"),
        ],
        ids=["connect_error", "read_error"],
    )
    def test_permanent_network_error_raises_immediately(self, monkeypatch, exc):
        """ConnectError/ReadError must raise without retrying (permanent errors)."""
        _, err = _fetch_err(monkeypatch, sequence(exc))
        assert err.attempts == 1

    def test_non_retryable_error_code_raises_immediately(self, monkeypatch):
        """A non-retryable Deezer error code must raise without retrying."""
        _, exc = _fetch_err(
            monkeypatch, sequence(error_envelope(200, 100, _PREVIEW_URL))
        )
        assert exc.attempts == 1
        assert exc.code == 100

    def test_non_ok_status_raises_immediately(self, monkeypatch):
        """A JSON-less non-200 routes to the error branch, raising with default code=0."""
        _, exc = _fetch_err(monkeypatch, response(403, url=_PREVIEW_URL))
        assert exc.attempts == 1
        assert exc.code == 0
