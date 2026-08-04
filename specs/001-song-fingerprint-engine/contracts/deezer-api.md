# External API Contract: Deezer Audio Integration

## 1. Search Track Endpoint

- **Endpoint**: `GET https://api.deezer.com/search`
- **Query Params**: `q={song_title}&limit=5`

### Sample Response Payload
```json
{
  "data": [
    {
      "id": 3135556,
      "isrc": "GBDUW0200059",
      "title": "Harder, Better, Faster, Stronger",
      "artist": { "name": "Daft Punk" },
      "album": { "title": "Discovery" },
      "preview": "https://cdns-preview-d.dzcdn.net/stream/c-d41b0b5..."
    }
  ],
  "total": 1
}
```

> **ISRC Persistence**: When the Deezer track response includes an `isrc` field, it is captured and persisted to the database alongside the platform track ID (`id`, stored as `deezer_id`). If `isrc` is absent, only the platform track ID is written and it serves as the fallback deduplication identifier.

## 2. Audio Snippet Download Contract

- **URL**: `preview` field from track response (HTTP GET)
- **Expected Formats**: MP3 audio stream (30 seconds)
- **Retry Rule**: 3 retries, 5-second interval on network failure before raising `NetworkDisconnectedError`.

## 3. Integration Scope & Future Evolution

- **Current Scope**: User-independent. Operates via public unauthenticated endpoints solely for song catalog search and 30-second audio preview snippet retrieval.
- **Future Scope**:
  - **Deezer**: Future versions may incorporate the `deezer-python` package for user authentication (OAuth) to access personal Deezer libraries and playlists.
  - **Multi-Provider Support**: This integration pattern will extend to other major music services (e.g., Spotify, YouTube Music, Apple Music, Amazon Music) to support user library access and authenticated catalog features.

