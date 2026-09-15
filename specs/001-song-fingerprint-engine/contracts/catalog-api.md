# Internal API Contract: Catalog endpoints

> Covers User Story 2 (Fingerprint Feature Retrieval & Inspection). Name chosen
> over `/api/songs/` to distinguish the *stored, fingerprinted* catalog from the
> `/api/search/` candidate list and from future user-library resources. Traceability:
> [traceability.md](traceability.md) §Internal Contract (`sa08`/`sa09`).

## 1. Catalog List Endpoint

- **Path**: `GET /api/catalog/`
- **Behavior**: Returns a summary list of all stored songs and their fingerprint metadata (US2 acceptance scenario 2). Empty catalog or zero stored rows → **200** with an empty `songs` array (not an error).
- **Response**:
```json
{
  "status": "success",
  "songs": [
    {
      "isrc": "GBDUW0000059",
      "deezer_id": 3135556,
      "title": "Harder, Better, Faster, Stronger",
      "artist": "Daft Punk",
      "artists": [{ "id": 27, "name": "Daft Punk" }],
      "album": "Discovery",
      "preview_url": "https://cdnt-preview.dzcdn.net/api/...",
      "duration": 226,
      "created_at": "2026-08-14T12:00:00Z",
      "fingerprint": {
        "spectral_centroid": 2154.32,
        "rms": 0.045,
        "spectral_bandwidth": 1820.15,
        "spectral_contrast": 18.42,
        "spectral_flatness": 0.012,
        "spectral_rolloff": 4350.80,
        "zero_crossing_rate": 0.085,
        "mfcc": 12.34
      }
    }
  ]
}
```

### Catalog List Response Field Reference

Each item in `songs` carries the full stored song metadata plus the collapsed 8-feature fingerprint (self-contained inspection; mirrors `data-model.md` `songs` + `song_fingerprints` columns).

| Field                                    | Type    | Format / Notes                                                      |
|------------------------------------------|---------|---------------------------------------------------------------------|
| `status`                                 | string  | `"success"` or `"error"`                                            |
| `songs`                                  | array   | List of stored catalog items; empty when nothing is stored          |
| `songs[].isrc`                           | string  | International Standard Recording Code (ISO 3901); unique            |
| `songs[].deezer_id`                      | integer | Deezer track ID (platform track ID)                                 |
| `songs[].title`                          | string  | Stored track title                                                  |
| `songs[].artist`                         | string  | Main artist name (denormalized from `song_artists` position 0)      |
| `songs[].artists`                        | array   | Main-first contributor list of `{id, name}` (stored `song_artists`) |
| `songs[].album`                          | string  | Album name; `null` when unset (`songs.album` is nullable)           |
| `songs[].preview_url`                    | string  | Stored Deezer 30-second preview URL                                 |
| `songs[].duration`                       | integer | Track duration in seconds                                           |
| `songs[].created_at`                     | string  | Record creation timestamp, ISO 8601 UTC                             |
| `songs[].fingerprint`                    | object  | Collapsed 8-feature vector (see fingerprint subfields below)        |
| `songs[].fingerprint.spectral_centroid`  | float   | Collapsed Spectral Centroid value (Hz)                              |
| `songs[].fingerprint.rms`                | float   | Collapsed Root Mean Square Energy value                             |
| `songs[].fingerprint.spectral_bandwidth` | float   | Collapsed Spectral Bandwidth value (Hz)                             |
| `songs[].fingerprint.spectral_contrast`  | float   | Collapsed Spectral Contrast value (dB)                              |
| `songs[].fingerprint.spectral_flatness`  | float   | Collapsed Spectral Flatness value                                   |
| `songs[].fingerprint.spectral_rolloff`   | float   | Collapsed Spectral Roll-off value (Hz)                              |
| `songs[].fingerprint.zero_crossing_rate` | float   | Collapsed Zero Crossing Rate value                                  |
| `songs[].fingerprint.mfcc`               | float   | Collapsed Mean MFCC summary value                                   |

- Every stored song has exactly one fingerprint (unique FK `song_id`), so each `songs[]` item carries its 8 scalars — the list is filter-free and mirrors the `songs` table directly.

### Catalog List Error Responses

| Status Code                 | Meaning                                                          | Body                                                    |
|-----------------------------|------------------------------------------------------------------|---------------------------------------------------------|
| `500 Internal Server Error` | Database failure while listing (unexpected; session rolled back) | `{"status": "error", "error": "internal server error"}` |

> **Empty catalog semantics**: An empty local database returns **200** with `{"status":"success","songs":[]}`. This mirrors the zero-match semantics precedent of the search endpoint (§1 of [search-api.md](search-api.md)) — absence of rows is data, not an error.

## 2. Catalog Detail Endpoint

- **Path**: `GET /api/catalog/{isrc}/`
- **Behavior**: Returns the structured full fingerprint detail and song metadata for the stored song matching `{isrc}` (US2 acceptance scenario 1).
- **Response**:
```json
{
  "status": "success",
  "song": {
    "isrc": "GBDUW0000059",
    "deezer_id": 3135556,
    "title": "Harder, Better, Faster, Stronger",
    "artist": "Daft Punk",
    "artists": [{ "id": 27, "name": "Daft Punk" }],
    "album": "Discovery",
    "preview_url": "https://cdnt-preview.dzcdn.net/api/...",
    "duration": 226,
    "created_at": "2026-08-14T12:00:00Z",
    "fingerprint": {
      "spectral_centroid": 2154.32,
      "rms": 0.045,
      "spectral_bandwidth": 1820.15,
      "spectral_contrast": 18.42,
      "spectral_flatness": 0.012,
      "spectral_rolloff": 4350.80,
      "zero_crossing_rate": 0.085,
      "mfcc": 12.34,
      "audio_format": "mp3",
      "sample_rate": 22050
    }
  }
}
```

### Catalog Detail Response Field Reference

Same item shape as §1 with the addition of the fingerprint provenance fields:

| Field                                                                                                                    | Type    | Format / Notes                                                      |
|--------------------------------------------------------------------------------------------------------------------------|---------|---------------------------------------------------------------------|
| `status`                                                                                                                 | string  | `"success"` or `"error"`                                            |
| `song`                                                                                                                   | object  | Stored song + fingerprint detail                                    |
| `song.isrc` / `.deezer_id` / `.title` / `.artist` / `.artists` / `.album` / `.preview_url` / `.duration` / `.created_at` | *_      | Same semantics as the list-item fields in §1                        |
| `song.fingerprint`                                                                                                       | object  | Collapsed 8-feature vector (same scalars as §1) + provenance fields |
| `song.fingerprint.audio_format`                                                                                          | string  | Stored snippet format, one of `mp3`/`wav`/`flac`/`ogg`/`m4a`        |
| `song.fingerprint.sample_rate`                                                                                           | integer | Sampling rate in Hz (default 22050)                                 |

### Catalog Detail Error Responses

| Status Code                 | Meaning                                                                                | Body                                                    |
|-----------------------------|----------------------------------------------------------------------------------------|---------------------------------------------------------|
| `404 Not Found`             | Empty/whitespace `{isrc}` or no stored song matches that `isrc` → `TrackNotFoundError` | `{"status": "error", "error": "TrackNotFoundError"}`    |
| `500 Internal Server Error` | Database failure while querying (unexpected; session rolled back)                      | `{"status": "error", "error": "internal server error"}` |

> **Unknown-ISRC semantics**: The detail endpoint is a lookup of a *stored* record, so an unmatched `{isrc}` is a client error (`404`), unlike the search endpoint where zero results are a valid `200` empty list. Matches the ISRC-reuse lookup used by `/api/confirm/` (REQ-009, REQ-008).

> **Reuse-lookup performance**: The ISRC lookup on this endpoint must meet the same under-500 ms target as the confirm reuse path — see §3.

## 3. Latency & Performance Requirements

| Endpoint / Path            | Scenario                     | Target                                             | Source       |
|----------------------------|------------------------------|----------------------------------------------------|--------------|
| `GET /api/catalog/{isrc}/` | Stored-record ISRC lookup    | MUST return in **under 500 ms**                    | Spec §SC-005 |
| `GET /api/catalog/`        | Full-catalog summary listing | No sub-second target defined; bounded by row count | Spec §SC-003 |

*Note: SC-005's under-500 ms target is shared with the `POST /api/confirm/` reuse path — both are single-row ISRC lookups over the `isrc` unique index.

## 4. Notes

- **Traceability**: `sa08` (`GET /api/catalog/`) and `sa09` (`GET /api/catalog/{isrc}/`) are registered in [traceability.md](traceability.md). The list endpoint has no dedicated REQ — US2 acceptance scenario 2 is its mandate; REQ-009 anchors the detail endpoint.
- **Future path growth**: US3 visualization is defined as `GET /api/catalog/{isrc}/visualization/` (feature-gated); the base path is stable for that extension.