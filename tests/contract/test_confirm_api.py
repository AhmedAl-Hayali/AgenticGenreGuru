"""Contract tests for POST /api/confirm/ endpoint.

GREEN phase: `confirm_view` is exercised as the REAL view. The two mocked
boundaries are `genreguru.fingerprint_service.process_fingerprint` (the
orchestration/service seam) and `views._get_session` (a fake session whose
`rollback`/`close` are recorded), so the view's own error handling — 201
success, 400 invalid JSON, 400 `AudioProcessingError`, 503
`NetworkDisconnectedError`, 500 unexpected, and `session.rollback()` on every
error path — is genuinely under test without network or DB writes.

The rollback/close assertions here implement the "NO partial Song/
SongFingerprint rows on error" contract guarantee at the view boundary
(T018/T019); the actual SAVEPOINT-isolation row assertions live in the
integration suites (repositories / fingerprint_service), which drive the real
persistence path. The real `genreguru_web.urls` → `fingerprint_app.urls`
routing is used via the default `ROOT_URLCONF`; the `/api/confirm/` POST
resolves to `confirm_view` through the live URL wiring.

With `CsrfViewMiddleware` in `MIDDLEWARE`, a confirm POST **without** a
matching `X-CSRFToken` header/cookie is rejected with 403 before the view
runs. These tests drive `django.test.Client(enforce_csrf_checks=True)` to
prove enforcement.
"""

import json
from typing import cast

import pytest
from fingerprint_app import views  # ty: ignore[unresolved-import]

from genreguru import fingerprint_service
from genreguru.dto import FingerprintResponse
from genreguru.errors import AudioProcessingError, NetworkDisconnectedError
from tests.sample_payloads import (
    DEEZER_CONFIRM_BODY,
    FINGERPRINT_FIELDS,
    SUCCESS_RESPONSE,
)


def confirm_body(resp) -> FingerprintResponse:
    """Return the typed confirm body (song_id/deezer_id/isrc/fingerprint)."""
    body = resp.json()
    assert isinstance(body, dict)
    return cast(FingerprintResponse, body)


def error_of(resp) -> str:
    """Return the typed `error` field of an error confirm response."""
    body = resp.json()
    assert isinstance(body, dict) and isinstance(body.get("error"), str)
    return body["error"]


def status_of(resp) -> str:
    """Return the typed `status` field (`success`|`error`) of a confirm response."""
    body = resp.json()
    assert isinstance(body, dict) and isinstance(body.get("status"), str)
    return body["status"]


def patch_session_and_process_fp(mocker, session_patch, process_fp_patch):
    """Patch session and `process_fingerprint` with provided stubs."""
    mocker.patch.object(views, "_get_session", new=session_patch)
    mocker.patch.object(
        fingerprint_service,
        "process_fingerprint",
        side_effect=process_fp_patch,
    )


@pytest.fixture
def post_confirm(django_client, mocker):
    """POST /api/confirm/ with stubbed service/session; returns the response.

    All arguments are keyword-only. `error` makes the service raise,
    `session` replaces the view's session (to assert rollback/close), and
    `body` overrides the posted match as a dict (default `DEEZER_MATCH`,
    JSON-encoded by the fixture).
    """

    def _post_confirm(
        *,
        error=None,
        session=None,
        body=None,
    ):
        def fake_process(fake_session, track, repo):
            if error is not None:
                raise error
            return dict(SUCCESS_RESPONSE)

        patch_session_and_process_fp(
            mocker,
            lambda: session or mocker.Mock(),
            fake_process,
        )

        payload = json.dumps(DEEZER_CONFIRM_BODY) if body is None else body

        return django_client.post(
            _CONFIRM_URL,
            data=payload,
            content_type="application/json",
        )

    return _post_confirm


_CONFIRM_URL = "/api/confirm/"


class TestConfirmSuccess:
    """Verify 201 response shape for a fresh fingerprint confirmation."""

    def test_status_201(self, post_confirm):
        """Successful confirm must return HTTP 201."""
        resp = post_confirm()
        assert resp.status_code == 201

    def test_status_success(self, post_confirm):
        """Response body must have `status` set to `success`."""
        resp = post_confirm()
        assert status_of(resp) == "success"

    def test_has_song_id_deezer_id_and_isrc(self, post_confirm):
        """Response must include `song_id`, `deezer_id`, and `isrc`."""
        resp = post_confirm()
        body = confirm_body(resp)
        assert "song_id" in body
        assert body["deezer_id"] == 3135556
        assert body["isrc"] == "GBDUW0000059"

    def test_fingerprint_has_all_8_dsp_features(self, post_confirm):
        """Fingerprint sub-object must contain all 8 DSP feature keys."""
        resp = post_confirm()
        fp = confirm_body(resp)["fingerprint"]
        for field in FINGERPRINT_FIELDS:
            assert field in fp, f"missing fingerprint field: {field}"
        assert fp["vector_length"] == 8

    def test_fingerprint_values_are_numeric(self, post_confirm):
        """All fingerprint feature values must be numeric (int or float)."""
        resp = post_confirm()
        fp = confirm_body(resp)["fingerprint"]
        for field in FINGERPRINT_FIELDS:
            assert isinstance(fp[field], (int, float)), f"{field} is not numeric"

    def test_success_closes_session_never_rolls_back(self, post_confirm, mocker):
        """Success must close the session once and never roll back."""
        session = mocker.Mock()
        resp = post_confirm(session=session)
        assert resp.status_code == 201
        session.close.assert_called_once()
        session.rollback.assert_not_called()


class TestConfirm400InvalidJSON:
    """Verify malformed request bodies yield 400."""

    def test_invalid_json(self, django_client):
        """A non-JSON body must produce HTTP 400 without touching the session."""
        resp = django_client.post(
            _CONFIRM_URL, data="{not json", content_type="application/json"
        )
        assert resp.status_code == 400
        assert status_of(resp) == "error"
        assert "invalid JSON" in error_of(resp)

    def test_missing_required_fields(self, post_confirm):
        """A JSON body missing required fields must produce HTTP 400."""
        resp = post_confirm(body={"title": "no other fields"})
        assert resp.status_code == 400
        assert status_of(resp) == "error"


class TestConfirmMethodEnforcement:
    """Verify POST-only enforcement on the confirm endpoint."""

    def test_get_is_rejected(self, django_client):
        """A GET to /api/confirm/ must be rejected with HTTP 405."""
        resp = django_client.get(_CONFIRM_URL)
        assert resp.status_code == 405


class TestConfirmErrorPaths:
    """Verify every service failure maps to its status and rolls back/closes the session."""

    @pytest.mark.parametrize(
        "error, status, message",
        [
            (
                AudioProcessingError("audio file cannot be processed"),
                400,
                "AudioProcessingError",
            ),
            (NetworkDisconnectedError("network"), 503, "NetworkDisconnectedError"),
            (RuntimeError("boom"), 500, "internal server error"),
        ],
        ids=["audio_processing_400", "network_503", "unexpected_500"],
    )
    def test_error_maps_status_and_rolls_back(
        self, post_confirm, mocker, error, status, message
    ):
        """An error from the service must map to its status and roll back the session."""
        session = mocker.Mock()
        resp = post_confirm(error=error, session=session)
        assert resp.status_code == status
        assert status_of(resp) == "error"
        assert error_of(resp) == message
        session.rollback.assert_called_once()
        session.close.assert_called_once()


class TestConfirmCsrf:
    """CSRF enforcement proofs for the confirm endpoint."""

    def test_post_without_token_is_rejected(self, django_csrf_client, mocker):
        """A confirm POST with no CSRF token must be blocked with 403.

        The service seam must not have been reached: patch it to raise if
        called, proving the middleware rejects before the view runs.
        """
        patch_session_and_process_fp(
            mocker,
            lambda: mocker.Mock(),
            AssertionError("view ran without CSRF token"),
        )

        resp = django_csrf_client.post(
            _CONFIRM_URL,
            data=json.dumps(DEEZER_CONFIRM_BODY),
            content_type="application/json",
        )

        assert resp.status_code == 403

    def test_post_with_token_succeeds(self, django_csrf_client, mocker):
        """After GET / issues the csrftoken cookie, a token-header POST passes.

        The rendered `{% csrf_token %}` in index.html sets the cookie; echoing
        it back as `X-CSRFToken` satisfies the middleware and the mocked
        service path returns 201.
        """
        index = django_csrf_client.get("/")
        assert index.status_code == 200
        token = django_csrf_client.cookies["csrftoken"].value
        assert token

        patch_session_and_process_fp(
            mocker,
            lambda: mocker.Mock(),
            lambda fake_session, track, repo: dict(SUCCESS_RESPONSE),
        )

        resp = django_csrf_client.post(
            _CONFIRM_URL,
            data=json.dumps(DEEZER_CONFIRM_BODY),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert resp.status_code == 201
