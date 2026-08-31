"""Integration test for snippet-fetch retry logic.

Verifies that `genreguru.deezer.snippets` retries QUOTA (4) / SERVICE_BUSY
(700) error codes and network timeouts up to its `_MAX_RETRIES`-attempt
budget, succeeds when a later attempt succeeds, and raises
`NetworkDisconnectedError` immediately for non-retryable Deezer error codes,
`ConnectError`, and non-200 statuses without an audio payload.

Tests fake the client's `httpx.get` with the shared `tests.http_stubs`
helpers. A `sequence` responder feeds events one per call: `httpx.Response`
items are returned, `Exception` items are raised (see
`tests.http_stubs.sequence`).
"""

import httpx
import pytest

from genreguru.deezer import snippets
from genreguru.errors import NetworkDisconnectedError
from tests.http_stubs import audio, capture_get, error_envelope, response, sequence

_PREVIEW_URL = (
    "https://cdnt-preview.dzcdn.net/api/1/1/abc/def/0/abc.mp3"
    "?hdnea=exp=123~acl=/api*~data=user_id=0~hmac=abc"
)

_FAKE_AUDIO = b"\x00" * 1024

_MAX_RETRIES = snippets._MAX_RETRIES  # single source of truth

_RETRYABLE_CODES = (4, 700)  # QUOTA, SERVICE_BUSY (client._RETRYABLE_CODES)

_SNIPPETS_HTTP_GET = "genreguru.deezer.snippets.httpx.get"


def _fetch(monkeypatch, responder):
    """Patch `httpx.get`, dispatch `fetch_snippet`, return (calls, result|error)."""
    calls = capture_get(monkeypatch, _SNIPPETS_HTTP_GET, responder)
    try:
        return calls, snippets.fetch_snippet(_PREVIEW_URL)
    except NetworkDisconnectedError as exc:
        return calls, exc


def _retry_then_success(failure):
    """A responder: *failure* repeated, then audio success on the last attempt."""
    ok = audio(_FAKE_AUDIO, _PREVIEW_URL)
    return sequence(*([failure] * (_MAX_RETRIES - 1)), ok)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Eliminate the 5s retry delay so the tests don't sleep between attempts."""
    monkeypatch.setattr("genreguru.deezer.snippets.time.sleep", lambda _: None)


class TestHappyPath:
    """Verify the single-call success path without retries."""

    def test_first_attempt_succeeds(self, monkeypatch):
        """A successful first fetch must return audio after a single call."""
        calls, result = _fetch(monkeypatch, audio(_FAKE_AUDIO, _PREVIEW_URL))
        assert result == _FAKE_AUDIO
        assert len(calls) == 1


class TestRetryableFailures:
    """Failures that trigger a retry, succeeding on the final attempt."""

    @pytest.mark.parametrize("code", _RETRYABLE_CODES)
    def test_retryable_error_code_then_success(self, monkeypatch, code):
        """A retryable Deezer error code must be retried, succeeding on the last attempt."""
        error = error_envelope(200, code, _PREVIEW_URL)
        calls, result = _fetch(monkeypatch, _retry_then_success(error))
        assert result == _FAKE_AUDIO
        assert len(calls) == _MAX_RETRIES

    @pytest.mark.parametrize("code", _RETRYABLE_CODES)
    def test_retryable_error_code_exhausts_budget(self, monkeypatch, code):
        """Repeated retryable codes must exhaust the budget, raising with the code."""
        error = error_envelope(200, code, _PREVIEW_URL)
        _, exc = _fetch(monkeypatch, sequence(*([error] * _MAX_RETRIES)))
        assert exc.attempts == _MAX_RETRIES
        assert exc.code == code

    def test_network_timeout_retries_then_success(self, monkeypatch):
        """ConnectTimeout must be retried and succeed on the final attempt."""
        timeout = httpx.ConnectTimeout("connection timed out")
        calls, result = _fetch(monkeypatch, _retry_then_success(timeout))
        assert result == _FAKE_AUDIO
        assert len(calls) == _MAX_RETRIES


class TestNonRetryableFailures:
    """Failures that raise immediately without retrying."""

    def test_connect_error_raises_immediately(self, monkeypatch):
        """ConnectError (e.g. DNS failure) must raise without retrying."""
        dns_res_fail = httpx.ConnectError("DNS resolution failed")
        _, exc = _fetch(monkeypatch, sequence(dns_res_fail))
        assert exc.attempts == 1

    @pytest.mark.parametrize("code", [100, 300])  # outside QUOTA/SERVICE_BUSY
    def test_non_retryable_error_code_raises_immediately(self, monkeypatch, code):
        """A non-retryable Deezer error code must raise without retrying."""
        _, exc = _fetch(monkeypatch, sequence(error_envelope(200, code, _PREVIEW_URL)))
        assert exc.attempts == 1
        assert exc.code == code

    @pytest.mark.parametrize("status", [403, 500])
    def test_non_ok_status_raises_immediately(self, monkeypatch, status):
        """A non-200 response without an audio payload must raise without retrying."""
        _, exc = _fetch(monkeypatch, response(status, url=_PREVIEW_URL))
        assert exc.attempts == 1
        assert exc.code == 0
