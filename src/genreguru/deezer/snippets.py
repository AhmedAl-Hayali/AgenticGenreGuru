"""Audio snippet fetcher with 3x retry / 5s delay.

Downloads a 30-second audio preview from Deezer.  Retries on QUOTA (4)
and SERVICE_BUSY (700) errors with a fixed 5-second interval.
Raises `NetworkDisconnectedError` after exhausting the 3-attempt
budget.

Module logger: INFO fetch start/success (bytes, elapsed), ERROR
`permanent network error` on `ConnectError`/`ReadError`; the retry
WARNING/ERROR logs and exhausted-budget `NetworkDisconnectedError` come
from `genreguru.deezer._retry.retry_until_success`. Never log bytes.
"""

import logging

import httpx

from genreguru.deezer._retry import RetryableError, retry_until_success
from genreguru.deezer.client import classify_error
from genreguru.errors import GenreguruError, NetworkDisconnectedError
from genreguru.gglogging import timer

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY = 5  # seconds


def fetch_snippet(preview_url: str) -> bytes:
    """Fetch audio bytes from *preview_url* with retry.

    Returns:
        Raw audio bytes on success.

    Raises:
        NetworkDisconnectedError: After exhausting the retry budget, or
            immediately for `ConnectError`, non-retryable Deezer error codes,
            or non-200 responses without an audio payload.
    """
    return retry_until_success(
        lambda attempt: _fetch_attempt(preview_url, attempt),
        max_retries=_MAX_RETRIES,
        delay=_RETRY_DELAY,
        operation_label="fetch_snippet",
    )


def _fetch_attempt(preview_url: str, attempt: int) -> bytes:
    """Execute one snippet-fetch attempt under `fetch_snippet`'s retry budget."""
    logger.info("fetch_snippet attempt=%d url=%s", attempt, preview_url)

    try:
        with timer() as elapsed:
            resp = httpx.get(preview_url, timeout=30)
    except (httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise RetryableError(code=None, last_exc=exc) from None
    except (httpx.ConnectError, httpx.ReadError) as exc:
        logger.error("permanent network error attempt=%d", attempt)
        raise NetworkDisconnectedError(
            f"network disconnected: {exc}", attempts=attempt
        ) from exc

    if resp.status_code == 200 and not resp.headers.get("content-type", "").startswith(
        "application/json"
    ):
        logger.info(
            "fetch_snippet success bytes=%d elapsed=%.3fs",
            len(resp.content),
            elapsed(),
        )
        return resp.content

    body = (
        resp.json()
        if resp.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    error_obj = body.get("error", {})
    error_code = error_obj.get("code", 0)

    try:
        classify_error(error_code)
    except GenreguruError:
        raise NetworkDisconnectedError(
            f"non-retryable deezer error code={error_code}",
            code=error_code,
            attempts=attempt,
        ) from None

    raise RetryableError(
        code=error_code,
        last_exc=NetworkDisconnectedError(
            f"deezer error code={error_code}",
            code=error_code,
            attempts=attempt,
        ),
    )
