"""Unit tests for the shared retry-with-backoff helper `genreguru.deezer._retry`.

Covers the `retry_until_success` contract in isolation: parameter guards,
control flow (success / retry / exhaustion / permanent propagation), and the
WARNING/ERROR log records. Network-path behavior built on this helper is
exercised by `tests.unit.test_deezer_client` and
`tests.integration.test_snippet_retry`.
"""

import logging

import httpx
import pytest

from genreguru.deezer._retry import RetryableError, retry_until_success
from genreguru.errors import NetworkDisconnectedError

_OP = "test operation"

_MAX_RETRIES = 3  # single retry budget for the control-flow suite
DELAY = 1.0

_LOGGER_NAME = "genreguru.deezer._retry"


def _run(attempt) -> object:
    """Dispatch *attempt* under the shared retry budget."""
    return retry_until_success(
        attempt, max_retries=_MAX_RETRIES, delay=DELAY, operation_label=_OP
    )


def _retry_log_records(caplog) -> list[str]:
    """Messages logged by the retry helper during a test."""
    return [r.getMessage() for r in caplog.records if r.name == _LOGGER_NAME]


class TestParameterGuards:
    """Verify invalid retry configuration is rejected loudly."""

    def test_max_retries_zero_rejected(self):
        """A non-positive-integer retry budget must raise ValueError."""
        with pytest.raises(ValueError, match="max_retries must be >= 1"):
            retry_until_success(
                lambda _n: "ok", max_retries=0, delay=0.1, operation_label=_OP
            )

    def test_negative_delay_rejected(self):
        """A negative delay must raise ValueError."""
        with pytest.raises(ValueError, match="delay must be >= 0"):
            retry_until_success(
                lambda _n: "ok", max_retries=1, delay=-1.0, operation_label=_OP
            )


class TestControlFlow:
    """Verify the attempt/retry/exhaustion control flow."""

    def test_success_first_attempt(self):
        """A successful first attempt returns immediately without retrying."""
        calls: list[int] = []

        def attempt(n: int) -> str:
            calls.append(n)
            return "ok"

        assert _run(attempt) == "ok"
        assert calls == [1]

    def test_retries_then_success(self):
        """A transient failure must be retried, succeeding on a later attempt."""
        calls: list[int] = []

        def attempt(n: int) -> str:
            calls.append(n)
            if n < _MAX_RETRIES:
                raise RetryableError(code=4, last_exc=ValueError("quota"))
            return "ok"

        assert _run(attempt) == "ok"
        assert calls == list(range(1, _MAX_RETRIES + 1))

    def test_exhausts_budget(self):
        """Exhausting the budget must raise, carrying attempts, code, and cause."""
        last = ValueError("busy")

        def attempt(_n: int) -> str:
            raise RetryableError(code=700, last_exc=last)

        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _run(attempt)
        assert exc_info.value.attempts == _MAX_RETRIES
        assert exc_info.value.code == 700
        assert exc_info.value.__cause__ is last

    def test_timeout_exhausts_budget_sets_code_none(self):
        """A budget exhausted only by timeouts propagates code=None to the error."""

        def attempt(_n: int) -> str:
            raise RetryableError(code=None, last_exc=httpx.ConnectTimeout("t"))

        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _run(attempt)
        assert exc_info.value.attempts == _MAX_RETRIES
        assert exc_info.value.code is None

    def test_permanent_error_propagates_untouched(self):
        """A non-RetryableError exception must propagate unchanged."""
        permanent = NetworkDisconnectedError("boom", attempts=1)

        def attempt(_n: int) -> str:
            raise permanent

        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _run(attempt)
        assert exc_info.value is permanent

    def test_base_exception_propagates(self):
        """A BaseException (e.g. KeyboardInterrupt) must not be swallowed."""

        def attempt(_n: int) -> str:
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            _run(attempt)


class TestLogging:
    """Verify the helper's WARNING/ERROR records."""

    def test_warning_on_retry(self, caplog):
        """Each retry must emit a WARNING naming the code and delay."""

        def attempt(n: int) -> str:
            if n < _MAX_RETRIES:
                raise RetryableError(code=4, last_exc=ValueError("quota"))
            return "ok"

        with caplog.at_level(logging.WARNING):
            _run(attempt)

        messages = _retry_log_records(caplog)
        retries = [m for m in messages if m.startswith("retryable error code=")]
        assert len(retries) == _MAX_RETRIES - 1
        assert "code=4" in retries[0]
        assert f"delay={DELAY:.1f}" in retries[0]

    def test_error_on_exhaustion(self, caplog):
        """An exhausted budget must emit an ERROR naming the operation."""

        def attempt(_n: int) -> str:
            raise RetryableError(code=700, last_exc=ValueError("busy"))

        with caplog.at_level(logging.ERROR), pytest.raises(NetworkDisconnectedError):
            _run(attempt)

        messages = _retry_log_records(caplog)
        assert f"{_OP} failed after {_MAX_RETRIES} attempts" in messages
