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
      "title": "Harder, Better, Faster, Stronger",
      "artist": "Daft Punk",
      "album": "Discovery",
      "preview_url": "https://cdns-preview-d.dzcdn.net/stream/..."
    }
  ]
}
```

## 2. Confirm & Fingerprint Endpoint

- **Path**: `POST /api/confirm/`
- **Request Body**:
```json
{
  "deezer_id": "3135556",
  "title": "Harder, Better, Faster, Stronger",
  "artist": "Daft Punk",
  "preview_url": "https://cdns-preview-d.dzcdn.net/stream/..."
}
```
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
*Note: In V1, each feature's temporal vector is collapsed (downsampled) to a single scalar feature value. Future editions may retain temporal dimensions with less downsampling.*
- **Error Responses**:
  - `400 Bad Request`: `{"status": "error", "message": "audio file cannot be processed"}`
  - `503 Service Unavailable`: `{"status": "error", "message": "network disconnected"}`
