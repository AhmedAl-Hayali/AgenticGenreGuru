"""Shared exception hierarchy for `genreguru`.

Each exception carries machine-readable attributes (`isrc`, `deezer_id`,
`code`, `attempts`) so catch sites can populate structured log context via
the fingerprint adapter (see `genreguru.gglogging`) without string
parsing.

No `logging` calls are made inside exception classes (SRP); logging happens
at the raise/catch boundary. Design authority:
[`docs/001-song-fingerprint-engine/logging-report.md`](https://github.com/AhmedAl-Hayali/AgenticGenreGuru/blob/main/docs/001-song-fingerprint-engine/logging-report.md)
§3.
"""

__all__ = [
    "GenreguruError",
    "NetworkDisconnectedError",
    "AudioProcessingError",
    "TrackNotFoundError",
    "MissingISRCError",
    "PreviewUnavailableError",
]


class GenreguruError(Exception):
    """Base class for all domain errors.

    Args:
        isrc: International Standard Recording Code, when known.
        deezer_id: Deezer track ID, when known.
        code: Machine-readable error code (e.g. a Deezer API error code).
        attempts: Number of attempts made (network retry paths).

    Subclasses:
        - `NetworkDisconnectedError`;
        - `AudioProcessingError`;
        - `TrackNotFoundError`;
        - `MissingISRCError`;
        - `PreviewUnavailableError`.
    """

    def __init__(
        self,
        message: str,
        *,
        isrc: str | None = None,
        deezer_id: int | None = None,
        code: int | str | None = None,
        attempts: int | None = None,
    ) -> None:
        super().__init__(message)
        self.isrc = isrc
        self.deezer_id = deezer_id
        self.code = code
        self.attempts = attempts

    def context(self) -> dict[str, str | int | None]:
        """Return the structured attributes for log `extra` enrichment.

        Returns:
            A dict with `isrc`, `deezer_id`, `code`, and `attempts`,
            omitting None keys.
        """
        return {
            attribute: attribute_value
            for attribute, attribute_value in (
                ("isrc", self.isrc),
                ("deezer_id", self.deezer_id),
                ("code", self.code),
                ("attempts", self.attempts),
            )
            if attribute_value is not None
        }


class NetworkDisconnectedError(GenreguruError):
    """Raised when snippet fetching exhausts its retry budget."""


class AudioProcessingError(GenreguruError):
    """Raised when fetched audio data cannot be processed."""


class TrackNotFoundError(GenreguruError):
    """Raised when a track-matching search returns no tracks."""


class MissingISRCError(GenreguruError):
    """Raised when an external platform response omits the required ISRC."""


class PreviewUnavailableError(GenreguruError):
    """Raised when a track response omits or returns an empty audio preview URL."""
