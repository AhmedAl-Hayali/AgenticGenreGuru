"""Shared httpx response builders and patch helpers for Deezer tests.

The search-client and snippet-fetch suites both assemble `httpx.Response`
fixtures and fake the module's `httpx.get`; this centralizes that so they
can't drift. A *responder* is a fixed `httpx.Response` or a callable
`(*args, **kwargs) -> Response | raises`; `stub_get`/`capture_get` install
them on a dotted `target` path (e.g. `"genreguru.deezer.client.httpx.get"`)
via pytest's `monkeypatch`.
"""

import httpx

from genreguru.deezer import client as _client

_JSON_HEADERS = {"content-type": "application/json"}
_AUDIO_HEADERS = {"content-type": "audio/mpeg"}

# Deezer retryable error codes (QUOTA, SERVICE_BUSY) — sourced from the client's
# own set so the retry suites can't drift from the implementation.
RETRYABLE_CODES = tuple(sorted(_client._RETRYABLE_CODES))


def no_sleep(monkeypatch, module: str) -> None:
    """Eliminate the retry delay at the module dotted path.

    *module* points at a module that imports `time`, e.g.
    `"genreguru.deezer._retry"`; patches that module's `time.sleep` so
    retry tests don't sleep between attempts. `time` is a process-global
    singleton, so the argument only selects which module's `time` reference
    to patch; any module with a `time` attribute works.
    """
    monkeypatch.setattr(f"{module}.time.sleep", lambda _: None)


def retry_then_success(failure, success: httpx.Response, n_failures: int):
    """A responder: *failure* repeated *n_failures* times, then *success* (repeats).

    For a retry-with-backoff path: the first *n_failures* calls fail, the next
    succeeds (and `sequence` keeps yielding *success* for any further calls).
    *failure* may be an `httpx.Response` (returned) or an `Exception` (raised).
    """
    return sequence(*(tuple([failure] * n_failures) + (success,)))


def repeat(item, times: int):
    """A responder yielding *item* *times* times, then *item* repeats forever."""
    return sequence(*tuple([item] * times))


def response(
    status_code: int,
    *,
    json: dict | None = None,
    content: bytes | None = None,
    headers: dict | None = None,
    url: str,
    method: str = "GET",
) -> httpx.Response:
    """A non-network response pinned to `method url`."""
    return httpx.Response(
        status_code=status_code,
        json=json,
        content=content,
        headers=headers,
        request=httpx.Request(method, url),
    )


def ok_json(body: dict, url: str) -> httpx.Response:
    """A 200 response carrying *body* as JSON."""
    return response(200, json=body, url=url)


def error_envelope(status_code: int, error_code: int, url: str) -> httpx.Response:
    """A Deezer error-envelope response.

    The explicit `Content-Type: application/json` is what routes even a 200
    into the error branch of `snippets.fetch_snippet` (the audio branch
    requires a non-JSON content type).
    """
    return response(
        status_code,
        json={
            "error": {
                "type": "Exception",
                "message": f"Error code {error_code}",
                "code": error_code,
            }
        },
        headers=_JSON_HEADERS,
        url=url,
    )


def audio(content: bytes, url: str) -> httpx.Response:
    """A 200 `audio/mpeg` response with *content* as the body."""
    return response(200, content=content, headers=_AUDIO_HEADERS, url=url)


def sequence(*items):
    """A responder yielding *items* in order, then repeating the last.

    *items* may be responses (returned) or exceptions (raised), enabling
    alternating success/failure scenarios.
    """
    index = 0

    def responder(*_args, **_kwargs):
        nonlocal index
        item = items[min(index, len(items) - 1)]
        index += 1
        if isinstance(item, Exception):
            raise item
        return item

    return responder


def _fake_get(responder):
    """An `httpx.get`-shaped callable delegating to *responder*."""
    return lambda *a, **kw: responder(*a, **kw) if callable(responder) else responder


def stub_get(monkeypatch, target: str, responder) -> None:
    """Fake the module-level `httpx.get` at *target* with *responder*."""
    monkeypatch.setattr(target, _fake_get(responder))


def capture_get(monkeypatch, target: str, responder) -> list[tuple[tuple, dict]]:
    """Like `stub_get`, but also record `(args, kwargs)` per call."""
    calls: list[tuple[tuple, dict]] = []
    inner = _fake_get(responder)

    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return inner(*args, **kwargs)

    monkeypatch.setattr(target, fake)
    return calls
