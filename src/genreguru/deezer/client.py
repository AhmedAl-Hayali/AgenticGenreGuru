"""Deezer search client.

`GET https://api.deezer.com/search?q={query}&limit=5` with field
mapping, fail-loud on missing ISRC / empty preview, and retry-with-backoff
for the retryable Deezer error codes (QUOTA 4, SERVICE_BUSY 700) per
`contracts/deezer-api.md`. `DATA_NOT_FOUND` (800) yields an empty result,
not an error, and a non-2xx/network failure raises
`NetworkDisconnectedError` so the API layer can map it to 503.

Module logger: INFO request query+limit and response `total`, DEBUG counts
only (no payload dumps), ERROR `logger.error` on missing ISRC / empty
preview. The retry budget and its WARNING/ERROR logs live in
`genreguru.deezer._retry.retry_until_success`; `RetryableError` is the
private transient-failure signal raised here that never escapes the budget.
"""

import logging
from typing import Literal, NoReturn

import httpx

from genreguru.deezer._retry import RetryableError, retry_until_success
from genreguru.dto import DeezerTrack
from genreguru.errors import (
    GenreguruError,
    MissingISRCError,
    NetworkDisconnectedError,
    PreviewUnavailableError,
)

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.deezer.com/search"
_LIMIT = 5

_RETRYABLE_CODES = {4, 700}  # QUOTA, SERVICE_BUSY
_DATA_NOT_FOUND = 800
_MAX_RETRIES = 3
_RETRY_DELAY = 5  # seconds


def _map_track(raw: dict) -> DeezerTrack:
    """Map a raw Deezer Track object to the internal schema."""
    return {
        "deezer_id": raw["id"],
        "title": raw["title"],
        "isrc": raw.get("isrc", ""),
        "duration": raw["duration"],
        "preview": raw.get("preview", ""),
        "artist": raw["artist"],
        "album": raw["album"],
    }


def _error_code(resp: httpx.Response) -> int | None:
    """Extract the Deezer error `code` from an error response body, or ``None``."""
    try:
        payload = resp.json()
    except ValueError:
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    return error.get("code")


def _validate_track(track: DeezerTrack) -> None:
    """Fail loud when a mapped *track* lacks a valid ISRC or preview URL."""
    if not track["isrc"]:
        logger.error("missing isrc for deezer_id=%s", track["deezer_id"])
        raise MissingISRCError(
            f"ISRC missing for deezer_id={track['deezer_id']}",
            deezer_id=track["deezer_id"],
        )
    if not track["preview"]:
        logger.error(
            "preview unavailable for deezer_id=%s isrc=%s",
            track["deezer_id"],
            track["isrc"],
        )
        raise PreviewUnavailableError(
            f"audio preview unavailable for deezer_id={track['deezer_id']}",
            isrc=track["isrc"],
            deezer_id=track["deezer_id"],
        )


def _build_tracks(body: dict) -> list[DeezerTrack]:
    """Map raw `data` tracks to the internal schema, validating each."""
    tracks = [_map_track(raw) for raw in body.get("data", [])]
    for track in tracks:
        _validate_track(track)
    return tracks


class DeezerSearchClient:
    """Deezer `/search` client with retry-with-backoff.

    Owns the endpoint, per-request limit/timeout, and retry budget so
    callers can tune them per instance. Holds only immutable configuration
    and the retry loop keeps per-call state in locals, so instances are safe
    for concurrent searches.
    """

    def __init__(
        self,
        *,
        base_url: str = _SEARCH_URL,
        limit: int = _LIMIT,
        request_timeout: float = 30.0,
        max_retries: int = _MAX_RETRIES,
        retry_delay: float = _RETRY_DELAY,
    ) -> None:
        self._base_url = base_url
        self._limit = limit
        self._request_timeout = request_timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def search(self, query: str) -> list[DeezerTrack]:
        """Search Deezer for *query*, returning up to `limit` mapped tracks.

        Retries QUOTA (4) / SERVICE_BUSY (700) up to the configured attempt
        budget with a fixed delay before raising `NetworkDisconnectedError`.
        `DATA_NOT_FOUND` (800) returns an empty list. Other Deezer error
        codes fail loudly, preserving the code; a non-2xx status or
        unparseable body raises `NetworkDisconnectedError` so the caller can
        map it to 503.

        Raises:
            MissingISRCError: If any returned track is missing an ISRC.
            PreviewUnavailableError: If any track has an empty/None preview URL.
            NetworkDisconnectedError: If the retry budget is exhausted or the
                response is not a valid search payload.
        """
        return retry_until_success(
            lambda attempt: self._try_search(query, attempt),
            max_retries=self._max_retries,
            delay=self._retry_delay,
            operation_label="deezer search",
        )

    def _try_search(self, query: str, attempt: int) -> list[DeezerTrack]:
        """Execute one search attempt under the caller's retry budget.

        Returns:
            list[DeezerTrack]: The mapped tracks on success, or an empty list
            on `DATA_NOT_FOUND` (800).

        Raises:
            RetryableError: If a retryable rate/busy code was seen.
            NetworkDisconnectedError: If the response is a non-retryable
                HTTP/network failure or an unparseable body.
            GenreguruError: If a non-retryable Deezer error code was returned.
        """
        logger.info(
            "deezer search attempt=%d query=%s limit=%d", attempt, query, self._limit
        )
        try:
            resp = httpx.get(
                self._base_url,
                params={"q": query, "limit": self._limit},
                timeout=self._request_timeout,
            )
            resp.raise_for_status()
            body = resp.json()
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            raise RetryableError(code=None, last_exc=exc) from None
        except (httpx.ConnectError, httpx.ReadError) as exc:
            raise NetworkDisconnectedError(
                f"network disconnected: {exc}", attempts=attempt
            ) from exc
        except httpx.HTTPStatusError as exc:
            if (code := _error_code(exc.response)) == _DATA_NOT_FOUND:
                return []
            _raise_for_error_code(code, attempt, exc, exc.response.status_code)
        except ValueError:
            raise NetworkDisconnectedError(
                "deezer search returned a non-JSON response", attempts=attempt
            ) from None

        if not isinstance(body, dict):
            raise NetworkDisconnectedError(
                "deezer search returned a non-object response body",
                attempts=attempt,
            ) from None

        error = body.get("error")
        if isinstance(error, dict):
            if (code := error.get("code")) == _DATA_NOT_FOUND:
                return []
            _raise_for_error_code(code, attempt, None, None)

        total = body.get("total", 0)
        logger.info("deezer search response total=%d", total)
        results = _build_tracks(body)
        logger.debug("mapped %d tracks", len(results))
        return results


def _raise_for_error_code(
    code: int | None,
    attempt: int,
    exc: Exception | None,
    status: int | None,
) -> NoReturn:
    """Map a non-`DATA_NOT_FOUND` Deezer error *code* to a raise.

    Retryable codes raise `RetryableError`; anything else raises the
    permanent failure the caller should propagate (*exc*/*status* when the
    failure came from the HTTP layer, `GenreguruError` for an embedded
    envelope).
    """
    if code in _RETRYABLE_CODES:
        last = exc or NetworkDisconnectedError(
            f"deezer search error code={code}", code=code, attempts=attempt
        )
        raise RetryableError(code=code, last_exc=last)
    if exc is not None:
        raise NetworkDisconnectedError(
            f"deezer search failed http_status={status} code={code}",
            code=code,
            attempts=attempt,
        ) from exc
    raise GenreguruError(f"non-retryable deezer error code={code}", code=code)


def classify_error(code: int) -> Literal[True]:
    """Classify a Deezer error code.

    Returns `True` for retryable codes (QUOTA=4, SERVICE_BUSY=700).
    Raises `GenreguruError` for non-retryable codes (including 800, which the
    search path special-cases to an empty result before it reaches here).
    """
    if code in _RETRYABLE_CODES:
        return True
    raise GenreguruError(f"non-retryable deezer error code={code}", code=code)
