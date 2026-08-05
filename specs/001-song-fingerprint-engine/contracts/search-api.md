# Internal API Contract: Django Frontend endpoints

## 1. Search Songs Endpoint

- **Path**: `GET /api/search/?query={song_name}`
- **Response**:
```json
{
  "status": "success",
  "matches": [
    {
      "deezer_id": "3135556",
      "isrc": "GBDUW0200059",
      "title": "Harder, Better, Faster, Stronger",
      "artist": "Daft Punk",
      "album": "Discovery",
      "preview_url": "https://cdns-preview-d.dzcdn.net/stream/..."
    }
  ]
}
```

### Search Response Field Reference

| Field                   | Type   | Format / Notes                                                                               |
|-------------------------|--------|----------------------------------------------------------------------------------------------|
| `status`                | string | `"success"` or `"error"`                                                                     |
| `matches`               | array  | List of match objects (top 5)                                                                |
| `matches[].deezer_id`   | string | Deezer track `id` (integer in the Deezer API) serialized as a decimal string                 |
| `matches[].isrc`        | string | ISO 39075 ISRC; mandatory, mirrors Deezer Track `isrc`                                       |
| `matches[].title`       | string | Track title; mirrors Deezer Track `title`                                                    |
| `matches[].artist`      | string | Artist name; flattened from Deezer `artist.name`                                             |
| `matches[].album`       | string | Album title; flattened from Deezer `album.title`                                             |
| `matches[].preview_url` | string | HTTPS URL of the 30-second MP3 preview; mirrors Deezer Track `preview` (may be empty string) |

## 2. Confirm & Fingerprint Endpoint

- **Path**: `POST /api/confirm/`
- **Request Body**:
```json
{
  "deezer_id": "3135556",
  "isrc": "GBDUW0200059",
  "title": "Harder, Better, Faster, Stronger",
  "artist": "Daft Punk",
  "preview_url": "https://cdns-preview-d.dzcdn.net/stream/..."
}
```

### Confirm Request Field Reference

| Field         | Type   | Format / Notes                                                               |
|---------------|--------|------------------------------------------------------------------------------|
| `deezer_id`   | string | Deezer track `id` (integer in the Deezer API) serialized as a decimal string |
| `isrc`        | string | ISO 39075 ISRC; mandatory when interfacing with external platforms           |
| `title`       | string | Track title                                                                  |
| `artist`      | string | Artist name                                                                  |
| `preview_url` | string | HTTPS URL of the 30-second MP3 preview                                       |

- **Response**:
```json
{
  "status": "success",
  "song_id": "3135556",
  "fingerprint": {
    "spectral_centroid": 2154.32,
    "rms": 0.045,
    "spectral_bandwidth": 1820.15,
    "spectral_contrast": 18.42,
    "spectral_flatness": 0.012,
    "spectral_rolloff": 4350.80,
    "zero_crossing_rate": 0.085,
    "mfcc": 12.34,
    "vector_length": 8
  }
}
```

### Confirm Response Field Reference

| Field                       | Type    | Format / Notes                                                                     |
|-----------------------------|---------|------------------------------------------------------------------------------------|
| `status`                    | string  | `"success"` or `"error"`                                                           |
| `song_id`                   | string  | Internal song record identifier (Deezer track `id` serialized as a decimal string) |
| `fingerprint`               | object  | Composite feature vector                                                           |
| `fingerprint.*`             | float   | Each acoustic feature collapses to a single scalar value in V1                     |
| `fingerprint.vector_length` | integer | Number of features (8 in V1)                                                       |

*Note: In V1, each feature's temporal vector is collapsed (downsampled) to a single scalar feature value. Future editions may retain temporal dimensions with less downsampling.*
- **Deduplication**: On confirm, the backend checks whether a song with the same `isrc` exists in the database. If a match is found, the stored fingerprint is reused and returned (no new feature vector is generated or stored). If no local record matches the `isrc`, the backend fetches the audio snippet, generates a new feature vector, and stores it with both `isrc` and `deezer_id` written to the database.
- **Error Responses**:
  - `400 Bad Request`: `{"status": "error", "message": "audio file cannot be processed"}`
  - `503 Service Unavailable`: `{"status": "error", "message": "network disconnected"}`
