# Phase 1 Data Model: Song Fingerprint Engine

## Database Schema (PostgreSQL via SQLAlchemy)

### Entity: `Song` (`songs` table)

Represents a track retrieved from Deezer search results.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer / UUID | Primary Key | Internal song record ID |
| `deezer_id` | String | Unique, Indexed, Not Null | Deezer track ID |
| `title` | String(255) | Not Null | Track title |
| `artist` | String(255) | Not Null | Artist name |
| `album` | String(255) | Nullable | Album name |
| `preview_url` | Text | Not Null | Deezer 30s preview MP3 URL |
| `duration` | Integer | Nullable | Track duration in seconds |
| `created_at` | DateTime (UTC) | Default: now() | Record creation timestamp |

### Entity: `SongFingerprint` (`song_fingerprints` table)

Represents extracted DSP acoustic feature vectors linked to a song.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer / UUID | Primary Key | Internal fingerprint ID |
| `song_id` | Integer / UUID | Foreign Key (`songs.id`), Unique, Not Null | Linked song ID |
| `spectral_centroid` | Float | Not Null | Collapsed Spectral Centroid value (Hz) |
| `rms` | Float | Not Null | Collapsed Root Mean Square Energy value |
| `spectral_bandwidth` | Float | Not Null | Collapsed Spectral Bandwidth value (Hz) |
| `spectral_contrast` | Float | Not Null | Collapsed Spectral Contrast value (dB) |
| `spectral_flatness` | Float | Not Null | Collapsed Spectral Flatness value |
| `spectral_rolloff` | Float | Not Null | Collapsed Spectral Roll-off value (Hz) |
| `zero_crossing_rate` | Float | Not Null | Collapsed Zero Crossing Rate value |
| `mfcc` | Float | Not Null | Collapsed Mean MFCC summary value |
| `audio_format` | String(10) | Not Null | Audio snippet format (e.g. mp3) |
| `sample_rate` | Integer | Default: 22050 | Sampling rate in Hz |
| `created_at` | DateTime (UTC) | Default: now() | Fingerprint extraction timestamp |

*Downsampling Strategy*: For Version 1, each acoustic feature's temporal vector is collapsed (downsampled) to a single scalar feature value to maintain a compact feature space. Future versions will support lower downsampling rates to retain temporal dynamics.

## Entity Relationship Diagram

```mermaid
erDiagram
    SONG ||--o| SONG_FINGERPRINT : "has 1-to-1 fingerprint"

    SONG {
        int id PK
        string deezer_id UK
        string title
        string artist
        string album
        string preview_url
        int duration
        datetime created_at
    }

    SONG_FINGERPRINT {
        int id PK
        int song_id FK, UK
        float spectral_centroid
        float rms
        float spectral_bandwidth
        float spectral_contrast
        float spectral_flatness
        float spectral_rolloff
        float zero_crossing_rate
        float mfcc
        string audio_format
        int sample_rate
        datetime created_at
    }
```

## State Transitions & Workflows

```mermaid
flowchart TD
    A["User Input Song Name"] --> B["Deezer API Search"]
    B -->|"Returns Top 5 Matches"| C["Display Candidates in UI"]
    C -->|"Click 1: Select Candidate"| D["Highlight Selected Track"]
    D -->|"Click 2: Confirm Selection"| E["Fetch Audio Snippet (Deezer)"]
    E -->|"Retry 3x on Network Fail"| F["DSP Feature Extraction"]
    F -->|"Extract 8 Collapsed Features"| G["Store via SQLAlchemy"]
    G --> H["Persist in songs & song_fingerprints Tables"]
```
