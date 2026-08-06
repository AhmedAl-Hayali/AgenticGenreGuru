# Internal API Contract: Django Frontend endpoints

## 1. Search Songs Endpoint

- **Path**: `GET /api/search/?query={song_name}`
- **Response**:
```json
{
  "status": "success",
  "matches": [
    {
      "deezer_id": 3135556,
      "title": "Harder, Better, Faster, Stronger",
      "isrc": "GBDUW0200059",
      "duration": 224,
      "preview": "https://cdns-preview-d.dzcdn.net/stream/...",
      "artist": { "id": 27, "name": "Daft Punk" },
      "album": { "id": 302127, "title": "Discovery" }
    }
  ]
}
```

### Search Response Field Reference

Each item in `matches` mirrors the Deezer Track object schema and field order (see [deezer-api.md](deezer-api.md) §1).

| Field                 | Type    | Format / Notes                                                                               |
|-----------------------|---------|----------------------------------------------------------------------------------------------|
| `status`              | string  | `"success"` or `"error"`                                                                     |
| `matches`             | array   | List of match objects (top 5)                                                                |
| `matches[].deezer_id` | integer | Deezer track `id` (integer in the Deezer API)                                                |
| `matches[].title`     | string  | Track title; mirrors Deezer Track `title`                                                    |
| `matches[].isrc`      | string  | ISO 39075 ISRC; mandatory, mirrors Deezer Track `isrc`                                       |
| `matches[].duration`  | integer | Track duration in seconds; mirrors Deezer Track `duration`                                   |
| `matches[].preview`   | string  | HTTPS URL of the 30-second MP3 preview; mirrors Deezer Track `preview` (may be empty string) |
| `matches[].artist`    | object  | Artist object: `id` (integer), `name` (string); mirrors Deezer `artist`                      |
| `matches[].album`     | object  | Album object: `id` (integer), `title` (string); mirrors Deezer `album`                       |

## 2. Confirm & Fingerprint Endpoint

- **Path**: `POST /api/confirm/`
- **Request Body**: Selected match object (same schema as `matches[]` in the search response):
```json
{
  "deezer_id": 3135556,
  "title": "Harder, Better, Faster, Stronger",
  "isrc": "GBDUW0200059",
  "duration": 224,
  "preview": "https://cdns-preview-d.dzcdn.net/stream/...",
  "artist": { "id": 27, "name": "Daft Punk" },
  "album": { "id": 302127, "title": "Discovery" }
}
```

### Confirm Request Field Reference

| Field       | Type    | Format / Notes                                                     |
|-------------|---------|--------------------------------------------------------------------|
| `deezer_id` | integer | Deezer track `id` (integer in the Deezer API)                      |
| `title`     | string  | Track title                                                        |
| `isrc`      | string  | ISO 39075 ISRC; mandatory when interfacing with external platforms |
| `duration`  | integer | Track duration in seconds                                          |
| `preview`   | string  | HTTPS URL of the 30-second MP3 preview                             |
| `artist`    | object  | Artist object: `id` (integer), `name` (string)                     |
| `album`     | object  | Album object: `id` (integer), `title` (string)                     |

- **Response**:
```json
{
  "status": "success",
  "song_id": "0195a1b8-0000-7000-8000-000000000000",
  "deezer_id": 3135556,
  "isrc": "GBDUW0000059",
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

| Field                            | Type    | Format / Notes                                     |
|----------------------------------|---------|----------------------------------------------------|
| `status`                         | string  | `"success"` or `"error"`                           |
| `song_id`                        | uuid    | Internal song record identifier (`songs` table PK) |
| `deezer_id`                      | integer | Deezer track ID (platform track ID)                |
| `isrc`                           | string  | International Standard Recording Code (ISO 39075); |
| `fingerprint`                    | object  | Composite feature vector                           |
| `fingerprint.spectral_centroid`  | float   | Collapsed Spectral Centroid value (Hz)             |
| `fingerprint.rms`                | float   | Collapsed Root Mean Square Energy value            |
| `fingerprint.spectral_bandwidth` | float   | Collapsed Spectral Bandwidth value (Hz)            |
| `fingerprint.spectral_contrast`  | float   | Collapsed Spectral Contrast value (dB)             |
| `fingerprint.spectral_flatness`  | float   | Collapsed Spectral Flatness value                  |
| `fingerprint.spectral_rolloff`   | float   | Collapsed Spectral Roll-off value (Hz)             |
| `fingerprint.zero_crossing_rate` | float   | Collapsed Zero Crossing Rate value                 |
| `fingerprint.mfcc`               | float   | Collapsed Mean MFCC summary value                  |
| `fingerprint.vector_length`      | integer | Number of features (8 in V1)                       |

*Note: In V1, each feature's temporal vector is collapsed (downsampled) to a single scalar feature value. Future editions may retain temporal dimensions with less downsampling.*
- **Deduplication**: On confirm, the backend checks whether a song with the same `isrc` exists in the database. If a match is found, the stored fingerprint is reused and returned (no new feature vector is generated or stored). If no local record matches the `isrc`, the backend fetches the audio snippet, generates a new feature vector, and stores it with both `isrc` and `deezer_id` written to the database.
- **Error Responses**:
  - `400 Bad Request`: `{"status": "error", "message": "audio file cannot be processed"}`
  - `503 Service Unavailable`: `{"status": "error", "message": "network disconnected"}`
