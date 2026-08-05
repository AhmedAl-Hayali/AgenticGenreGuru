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
      "isrc": "GBDUW0200059",
      "duration": 224,
      "preview": "https://cdns-preview-d.dzcdn.net/stream/c-d41b0b5...",
      "link": "https://www.deezer.com/track/3135556",
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
| `link`     | string  | HTTPS URL to the public Deezer track page                                       |
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
