"""Deezer API client (search + track lookup).

`GET https://api.deezer.com/search?q={query}&limit=5` for candidate matches
and `GET https://api.deezer.com/track/{id}` for a single track's full
`contributors` roster, with field mapping, fail-loud on missing ISRC / empty
preview, and retry-with-backoff for the retryable Deezer error codes (QUOTA
4, SERVICE_BUSY 700) per `contracts/deezer-api.md`. `DATA_NOT_FOUND` (800)
yields an empty search result and a `TrackNotFoundError` on track lookup,
not a generic error, and a non-2xx/network failure raises
`NetworkDisconnectedError` so the API layer can map it to 503.

Module logger: INFO request query+limit / track id and response `total`,
DEBUG counts only (no payload dumps), ERROR `logger.error` on missing ISRC /
empty preview. The retry budget and its WARNING/ERROR logs live in
`genreguru.deezer._retry.retry_until_success`; `RetryableError` is the
private transient-failure signal raised here that never escapes the budget.
"""

import logging
from typing import NoReturn

import httpx

from genreguru.deezer._retry import (
    RetryableError,
    is_retryable_code,
    retry_until_success,
)
from genreguru.dto import Artist, DeezerTrack
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
# Defensive fallback artist so the canonical `artists` list is never empty,
# even for a malformed upstream `artist`/`contributors` payload.
_UNKNOWN_ARTIST: Artist = {"id": 0, "name": "Unknown artist"}

_DATA_NOT_FOUND = 800
_MAX_RETRIES = 3
_RETRY_DELAY = 5  # seconds


def _norm_artist(raw: object) -> Artist | None:
    """Normalize a Deezer artist object to `Artist`, or `None` if malformed.

    Malformed entries (non-dict, missing/blank `name`, non-int `id`) are
    skipped, never propagated, per the tolerant `contributors` boundary.
    """
    if not isinstance(raw, dict):
        return None
    artist_id = raw.get("id")
    name = raw.get("name")
    if not isinstance(artist_id, int) or not isinstance(name, str) or not name:
        return None
    return {"id": artist_id, "name": name}


def _map_artists(raw_artist: object, contributors: object) -> list[Artist]:
    """Build the canonical main-first `artists` list for a Deezer track.

    The main `artist` always leads: Deezer's `/track/{id}` `contributors`
    carry the same id first when present (verified), so the main entry is
    deduplicated out of the roster. Malformed contributors are skipped; at
    least the main artist (or `_UNKNOWN_ARTIST`) is guaranteed, so the list
    is never empty.
    """
    artists: list[Artist] = []
    seen: set[int] = set()

    main_artist = _norm_artist(raw_artist)
    if main_artist is not None:
        artists.append(main_artist)
        seen.add(main_artist["id"])

    if isinstance(contributors, list):
        for entry in contributors:
            artist = _norm_artist(entry)
            if artist is None or artist["id"] in seen:
                continue
            artists.append(artist)
            seen.add(artist["id"])

    return artists or [_UNKNOWN_ARTIST]


def _map_track(raw: dict) -> DeezerTrack:
    """Map a raw Deezer Track object to the internal schema."""
    return {
        "deezer_id": raw["id"],
        "title": raw["title"],
        "isrc": raw.get("isrc", ""),
        "duration": raw["duration"],
        "preview": raw.get("preview", ""),
        "artist": raw["artist"],
        "artists": _map_artists(raw.get("artist"), raw.get("contributors")),
        "album": raw["album"],
    }


def _error_code(resp: httpx.Response) -> int | None:
    """Extract the Deezer error `code` from an error response body, or `None`."""
    try:
        payload = resp.json()
    except ValueError:
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    return error.get("code")


def _validate_track(track: DeezerTrack) -> None:
    """Validate that a mapped track contains a valid ISRC and preview URL.

    Raises:
        MissingISRCError: If the track is missing an ISRC.
        PreviewUnavailableError: If the track preview URL is empty.
    """
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


class DeezerClient:
    """Deezer API client (search + track lookup) with retry-with-backoff.

    Owns the endpoints, per-request limit/timeout, and retry budget so
    callers can tune them per instance. Holds only immutable configuration
    and the retry loop keeps per-call state in locals, so instances are safe
    for concurrent use.

    Args:
        base_url: Search API endpoint URL.
        track_url: Track lookup API endpoint base URL.
        limit: Default number of candidate tracks per search query.
        request_timeout: Seconds before HTTP request timeout.
        max_retries: Total request attempts allowed before budget exhaustion.
        retry_delay: Fixed delay in seconds between retry attempts.
        session: HTTPX client instance to use for requests, or None to use
            module-level default.
    """

    def __init__(
        self,
        *,
        base_url: str = _SEARCH_URL,
        track_url: str = _TRACK_URL,
        limit: int = _LIMIT,
        request_timeout: float = 30.0,
        max_retries: int = _MAX_RETRIES,
        retry_delay: float = _RETRY_DELAY,
        session: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url
        self._track_url = track_url
        self._limit = limit
        self._request_timeout = request_timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._session = session or httpx

    def _request_json(
        self,
        url: str,
        params: dict | None,
        attempt: int,
        label: str,
    ) -> tuple[dict, int | None]:
        """Execute an HTTP GET request and parse JSON payload / error envelope.

        Args:
            url: Target endpoint URL.
            params: Query parameters dictionary, or None if no parameters.
            attempt: Current retry attempt number (1-indexed).
            label: Human-readable operation label for logging context.

        Returns:
            Tuple of `(body_dict, deezer_error_code)`. On an embedded or
            HTTP 404 `DATA_NOT_FOUND` (800) code, returns `({}, _DATA_NOT_FOUND)`
            so the caller can choose whether to return an empty list (search)
            or raise `TrackNotFoundError` (lookup).

        Raises:
            RetryableError: If a retryable rate/busy code was seen.
            NetworkDisconnectedError: If the response is a non-retryable
                HTTP/network failure or an unparseable body.
            GenreguruError: If a non-retryable Deezer error code was returned.
        """
        try:
            resp = self._session.get(
                url,
                params=params,
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
                return {}, _DATA_NOT_FOUND
            _raise_for_error_code(code, attempt, exc, exc.response.status_code)
        except ValueError:
            raise NetworkDisconnectedError(
                f"deezer {label} returned a non-JSON response", attempts=attempt
            ) from None

        if not isinstance(body, dict):
            raise NetworkDisconnectedError(
                f"deezer {label} returned a non-object response body",
                attempts=attempt,
            ) from None

        error = body.get("error")
        if isinstance(error, dict):
            if (code := error.get("code")) == _DATA_NOT_FOUND:
                return {}, _DATA_NOT_FOUND
            _raise_for_error_code(code, attempt, None, None)

        return body, None

    def search(self, query: str) -> list[DeezerTrack]:
        """Search Deezer for candidate tracks matching a query.

        Retries QUOTA (4) / SERVICE_BUSY (700) up to the configured attempt
        budget with a fixed delay before raising `NetworkDisconnectedError`.
        `DATA_NOT_FOUND` (800) returns an empty list. Other Deezer error
        codes fail loudly, preserving the code; a non-2xx status or
        unparseable body raises `NetworkDisconnectedError` so the caller can
        map it to 503.

        Args:
            query: Free-text search query string.

        Returns:
            List of validated Deezer tracks matching the query, up to `limit`.

        Raises:
            MissingISRCError: If any returned track is missing an ISRC.
            PreviewUnavailableError: If any track has an empty/None preview URL.
            NetworkDisconnectedError: If the retry budget is exhausted or the
                response is not a valid search payload.
            GenreguruError: If a non-retryable Deezer error code is returned.
        """
        return retry_until_success(
            lambda attempt: self._try_search(query, attempt),
            max_retries=self._max_retries,
            delay=self._retry_delay,
            operation_label="deezer search",
        )

    def _try_search(self, query: str, attempt: int) -> list[DeezerTrack]:
        """Execute one search attempt under the caller's retry budget.

        Args:
            query: Free-text search query string.
            attempt: Current attempt number (1-indexed).

        Returns:
            Mapped tracks on success, or an empty list on `DATA_NOT_FOUND` (800).

        Raises:
            RetryableError: If a retryable rate/busy code was seen.
            NetworkDisconnectedError: If the response is a non-retryable
                HTTP/network failure or an unparseable body.
            GenreguruError: If a non-retryable Deezer error code was returned.
        """
        logger.info(
            "deezer search attempt=%d query=%s limit=%d", attempt, query, self._limit
        )
        body, err_code = self._request_json(
            self._base_url,
            {"q": query, "limit": self._limit},
            attempt,
            "search",
        )
        if err_code == _DATA_NOT_FOUND:
            return []

        total = body.get("total", 0)
        logger.info("deezer search response total=%d", total)
        results = _build_tracks(body)
        logger.debug("mapped %d tracks", len(results))
        return results

    def get_track(self, track_id: int) -> DeezerTrack:
        """Fetch one track by id, including the full `contributors` roster.

        Uses the same retry-with-backoff budget and validation as `search`.
        `DATA_NOT_FOUND` (800) raises `TrackNotFoundError` so the caller can
        skip the missing track (best-effort enrichment) without aborting.

        Args:
            track_id: Deezer track identifier.

        Returns:
            Mapped and validated Deezer track with full contributor roster.

        Raises:
            TrackNotFoundError: If Deezer returns `DATA_NOT_FOUND` for the id.
            MissingISRCError: If the track lacks an ISRC.
            PreviewUnavailableError: If the track has an empty/None preview URL.
            NetworkDisconnectedError: If the retry budget is exhausted or the
                response is not a valid track payload.
            GenreguruError: If a non-retryable Deezer error code is returned.
        """
        return retry_until_success(
            lambda attempt: self._try_get_track(track_id, attempt),
            max_retries=self._max_retries,
            delay=self._retry_delay,
            operation_label="deezer track lookup",
        )

    def _try_get_track(self, track_id: int, attempt: int) -> DeezerTrack:
        """Execute one track lookup under the caller's retry budget.

        Args:
            track_id: Deezer track identifier.
            attempt: Current attempt number (1-indexed).

        Returns:
            Mapped Deezer track payload.

        Raises:
            RetryableError: If a retryable rate/busy code was seen.
            TrackNotFoundError: If `DATA_NOT_FOUND` (800) was returned.
            NetworkDisconnectedError: If the response is a non-retryable
                HTTP/network failure or an unparseable body.
            GenreguruError: If a non-retryable Deezer error code was returned.
        """
        logger.info("deezer track lookup attempt=%d track_id=%s", attempt, track_id)
        url = f"{self._track_url}/{track_id}"
        body, err_code = self._request_json(url, None, attempt, "track lookup")
        if err_code == _DATA_NOT_FOUND:
            return []
            raise TrackNotFoundError(f"track not found: {track_id}", deezer_id=track_id)

        track = _map_track(body)
        _validate_track(track)
        return track


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
    """Map a non-`DATA_NOT_FOUND` Deezer error code to an exception raise.

    Retryable codes raise `RetryableError`; anything else raises the
    permanent failure the caller should propagate (`exc`/`status` when the
    failure came from the HTTP layer, `GenreguruError` for an embedded
    envelope).

    Args:
        code: Deezer error code, or None if no code present.
        attempt: Current retry attempt number (1-indexed).
        exc: Underlying exception if raised during request, or None.
        status: HTTP status code, or None if response body error.

    Raises:
        RetryableError: If the error code is retryable.
        NetworkDisconnectedError: If the error is an HTTP/network failure.
        GenreguruError: If the error is a non-retryable Deezer error envelope.
    """
    if is_retryable_code(code):
        last = exc or NetworkDisconnectedError(
            f"deezer error code={code}", code=code, attempts=attempt
        )
        raise RetryableError(code=code, last_exc=last)
    if exc is not None:
        raise NetworkDisconnectedError(
            f"deezer request failed http_status={status} code={code}",
            code=code,
            attempts=attempt,
        ) from exc
    raise GenreguruError(f"non-retryable deezer error code={code}", code=code)
