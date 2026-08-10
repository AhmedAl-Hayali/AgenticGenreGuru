# External API Contract: Deezer Audio Integration

## 1. Search Track Endpoint

- **Endpoint**: `GET https://api.deezer.com/search`
- **Query Params**: `q={song_title}&limit=5`
- **Response Shape**: JSON object with `data` (array of Track objects) and `total` (integer).

### Sample Response Payload
```json
{
  "data": [
    {
      "id": 3135556,
      "title": "Harder, Better, Faster, Stronger",
      "isrc": "GBDUW0000059",
      "duration": 226,
      "preview": "https://cdnt-preview.dzcdn.net/api/...",
      "artist": { "id": 27, "name": "Daft Punk" },
      "album": { "id": 302127, "title": "Discovery" }
    }
  ],
  "total": 1
}
```

### Track Object Field Reference

Per the official Deezer API reference (`https://developers.deezer.com/api/search`), each item in `data` is a Track object. Only the fields consumed by GenreGuru are listed.

| Field      | Type    | Description                                                                     |
|------------|---------|---------------------------------------------------------------------------------|
| `id`       | integer | Deezer track ID (persisted as `deezer_id`)                                      |
| `title`    | string  | Track title                                                                     |
| `isrc`     | string  | ISO 39075 International Standard Recording Code (mandatory)                     |
| `duration` | integer | Track duration in seconds                                                       |
| `preview`  | string  | HTTPS URL of the 30-second MP3 preview; may be an empty string when unavailable |
| `artist`   | object  | Artist object: `id` (integer), `name` (string)                                  |
| `album`    | object  | Album object: `id` (integer), `title` (string)                                  |

> **ISRC Persistence**: The Deezer track response MUST include an `isrc` field; it is captured and persisted to the database alongside the platform track ID (`id`, stored as `deezer_id`). If `isrc` is absent in the external response, the system MUST fail loudly and throw an error rather than persisting the track without it.

## 2. Audio Snippet Download Contract

- **URL**: `preview` field from track response (HTTP GET)
- **Expected Formats**: MP3 audio stream (30 seconds)
- **Retry Rule**: 3 retries, 5-second interval on network failure before raising `NetworkDisconnectedError`.

## 3. Integration Scope & Future Evolution

- **Current Scope**: User-independent. Operates via public unauthenticated endpoints solely for song catalog search and 30-second audio preview snippet retrieval.
- **Future Scope**:
  - **Deezer**: Future versions may incorporate the `deezer-python` package for user authentication (OAuth) to access personal Deezer libraries and playlists.
  - **Multi-Provider Support**: This integration pattern will extend to other major music services (e.g., Spotify, YouTube Music, Apple Music, Amazon Music) to support user library access and authenticated catalog features.

## 4. Error Responses

Per the official Deezer [API errors](`https://developers.deezer.com/api/errors`) reference, the API returns an error envelope when a request fails.

### Error Envelope Shape
```json
{
  "error": {
    "type": "Exception",
    "message": "Quota limit exceeded",
    "code": 4
  }
}
```

### Relevant Error Codes

| Constant                         | Type                                          | Code |
|----------------------------------|-----------------------------------------------|------|
| `QUOTA`                          | `Exception`                                   | 4    |
| `ITEMS_LIMIT_EXCEEDED`           | `Exception`                                   | 100  |
| `PERMISSION`                     | `OAuthException`                              | 200  |
| `TOKEN_INVALID`                  | `OAuthException`                              | 300  |
| `PARAMETER`                      | `ParameterException`                          | 500  |
| `PARAMETER_MISSING`              | `MissingParameterException`                   | 501  |
| `QUERY_INVALID`                  | `InvalidQueryException`                       | 600  |
| `SERVICE_BUSY`                   | `Exception`                                   | 700  |
| `DATA_NOT_FOUND`                 | `DataException`                               | 800  |
| `INDIVIDUAL_ACCOUNT_NOT_ALLOWED` | `IndividualAccountChangedNotAllowedException` | 901  |

### Scope Mapping

| Code | Constant                         | Relevance in GenreGuru                                                                          |
|------|----------------------------------|-------------------------------------------------------------------------------------------------|
| 4    | `QUOTA`                          | Current. Search quota exhausted → retry with backoff, then propagate `NetworkDisconnectedError` |
| 100  | `ITEMS_LIMIT_EXCEEDED`           | Current. `limit` param (5) too high / result cap hit → reduce request limit                     |
| 200  | `PERMISSION`                     | Current. Resource access denied → fail loudly with code preserved                               |
| 300  | `TOKEN_INVALID`                  | Future (OAuth). Public endpoints unauthenticated, not applicable now                            |
| 500  | `PARAMETER`                      | Current. Wrong param in request → developer bug, fail loudly                                    |
| 501  | `PARAMETER_MISSING`              | Current. Missing param (e.g., `q`) → developer bug, fail loudly                                 |
| 600  | `QUERY_INVALID`                  | Current. Malformed search query → fail loudly, log query                                        |
| 700  | `SERVICE_BUSY`                   | Current. Server overload → retry with backoff before failing                                    |
| 800  | `DATA_NOT_FOUND`                 | Current. No matching track → return empty result, not an error                                  |
| 901  | `INDIVIDUAL_ACCOUNT_NOT_ALLOWED` | Not applicable. Individual account restriction, out of public search scope                      |

> **Handling Rule**: On `QUOTA` (4) and `SERVICE_BUSY` (700), retry with backoff before propagating `NetworkDisconnectedError`. `DATA_NOT_FOUND` (800) yields empty search results. All other codes fail loudly, preserving the Deezer error `type`/`message`/`code`.
