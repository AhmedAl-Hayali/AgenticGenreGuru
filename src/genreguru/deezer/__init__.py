"""Deezer API integration: catalog search and audio preview retrieval.

Submodules:

- `.client` — `DeezerClient().search()`: song-title search against
  `GET https://api.deezer.com/search?q=...&limit=5`, Track field mapping
  (artist + contributors → `artists`, cover from `md5_image`),
  fail-loud on missing `isrc` (`MissingISRCError`) / empty `preview`
  (`PreviewUnavailableError`), and error-code classification
  (`classify_error`: `QUOTA`(4) / `SERVICE_BUSY`(700) retryable).
  `get_track()`: single-track lookup against
  `GET https://api.deezer.com/track/{id}` → `TrackNotFoundError` on
  404/`DATA_NOT_FOUND`(800).
- `.snippets` — `snippets.fetch_snippet()`: 30-second audio preview
  download with 3 attempts / 5 s delay, raising
  `NetworkDisconnectedError` after exhausting the budget.

Contract authority:
[`specs/001-song-fingerprint-engine/contracts/deezer-api.md`](https://github.com/AhmedAl-Hayali/AgenticGenreGuru/blob/main/specs/001-song-fingerprint-engine/contracts/deezer-api.md).
"""
