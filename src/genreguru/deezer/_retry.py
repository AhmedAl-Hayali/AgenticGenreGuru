"""Shared retry-with-backoff loop for Deezer HTTP calls.

`retry_until_success` runs an *attempt* callable under a fixed budget with a
fixed delay between attempts. The attempt callable either returns a success
value, raises `RetryableError` to request another attempt, or raises any
other exception to fail immediately (a permanent error, propagated
unchanged).

Retrying is control flow, so a transient result is signaled by an exception
rather than a return-value union: it lets the attempt function `return` a
success value directly and keeps `raise ... from` chains intact.

Module logger: WARNING per retry, ERROR on an exhausted budget.
"""

import logging
import time
from collections.abc import Callable

from genreguru.errors import NetworkDisconnectedError

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Internal control-flow signal for a transient, retryable failure.

    Raised by an attempt callable passed to `retry_until_success` and caught
    there; never escapes. Carries the last exception and Deezer error code.
    """

    def __init__(self, *, code: int | None, last_exc: Exception) -> None:
        super().__init__(f"retryable error code={code or ''}")
        self.code = code
        self.last_exc = last_exc


def retry_until_success[T](
    attempt: Callable[[int], T],
    *,
    max_retries: int,
    delay: float,
    operation_label: str,
) -> T:
    """Run *attempt* up to *max_retries* times, retrying `RetryableError`.

    Args:
        attempt: One attempt, ``attempt(n)`` with *n* 1-based; see the module
            docstring for the return/raise contract.
        max_retries: Total attempts before the budget is exhausted.
        delay: Fixed seconds to sleep between attempts.
        operation_label: Used in the exhausted-budget log and message, e.g.
            ``"deezer search"`` yields ``"deezer search failed after N
            attempts"``.

    Returns:
        The first successful *attempt* value.

    Raises:
        ValueError: If *max_retries* < 1 or *delay* < 0.
        NetworkDisconnectedError: If the budget is exhausted; carries
            ``attempts=max_retries`` and the last retryable error ``code``.
        Any exception raised by *attempt* other than `RetryableError`
            propagates unchanged.
    """
    if max_retries < 1:
        raise ValueError(f"max_retries must be >= 1, got {max_retries}")
    if delay < 0:
        raise ValueError(f"delay must be >= 0, got {delay}")

    last_exc: Exception | None = None
    last_error_code: int | None = None

    for attempt_no in range(1, max_retries + 1):
        try:
            return attempt(attempt_no)
        except RetryableError as retry:
            last_exc, last_error_code = retry.last_exc, retry.code
            if attempt_no < max_retries:
                logger.warning(
                    "retryable error code=%s attempt=%d delay=%s",
                    last_error_code,
                    attempt_no,
                    delay,
                )
                time.sleep(delay)

    logger.error(
        "%s failed after %d attempts",
        operation_label,
        max_retries,
        exc_info=last_exc,
    )
    raise NetworkDisconnectedError(
        f"{operation_label} failed after {max_retries} attempts",
        attempts=max_retries,
        code=last_error_code,
    ) from last_exc
