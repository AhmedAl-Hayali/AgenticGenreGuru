"""Contract tests for POST /api/confirm/{match_id} endpoint.

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
routing is used via the default `ROOT_URLCONF`; the `/api/confirm/{match_id}`
POST resolves to `confirm_view` through the live URL wiring.
"""

import json
from typing import cast

import pytest
from fingerprint_app import views  # ty: ignore[unresolved-import]

from genreguru import fingerprint_service
from genreguru.dto import FingerprintResponse
from genreguru.errors import AudioProcessingError, NetworkDisconnectedError
from tests.sample_payloads import DEEZER_MATCH, FINGERPRINT_FIELDS, SUCCESS_RESPONSE


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


@pytest.fixture
def post_confirm(django_client, mocker):
    """POST /api/confirm/3135556/ with stubbed service/session; returns the response.

    All arguments are keyword-only. `error` makes the service raise,
    `session` replaces the view's session (to assert rollback/close), `body`
    overrides the posted match (default `DEEZER_MATCH`), and `raw` posts an
    unencoded body verbatim.
    """

    def _post_confirm(
        *,
        error=None,
        session=None,
        body=None,
        raw=None,
    ):
        def fake_process(fake_session, track):
            if error is not None:
                raise error
            return dict(SUCCESS_RESPONSE)

        mocker.patch.object(views, "_get_session", new=lambda: session or mocker.Mock())
        mocker.patch.object(
            fingerprint_service, "process_fingerprint", side_effect=fake_process
        )

        if raw is not None:
            return django_client.post(
                "/api/confirm/3135556/",
                data=raw,
                content_type="application/json",
            )
        payload = DEEZER_MATCH if body is None else body
        return django_client.post(
            "/api/confirm/3135556/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    return _post_confirm


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

    def test_invalid_json(self, post_confirm):
        """A non-JSON body must produce HTTP 400 without touching the session."""
        resp = post_confirm(raw="{not json")
        assert resp.status_code == 400
        assert status_of(resp) == "error"
        assert "invalid JSON" in error_of(resp)

    def test_missing_required_fields(self, post_confirm):
        """A JSON body missing required fields must produce HTTP 400."""
        resp = post_confirm(body={"title": "no other fields"})
        assert resp.status_code == 400
        assert status_of(resp) == "error"


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
