# Feature Specification: Song Fingerprint Engine

**Feature Branch**: `001-song-fingerprint-engine`

**Created**: 2026-08-03

**Status**: Draft

**Input**: User description: "Develop GenreGuru, a feature engineering tool with a song name as its input and processing that is fetching a song snippet from online, generating a song fingerprint using audio digital signal processing. the features that compose the song fingerprint should be stored in a local relational database. This stored data will later be used to expand the program and efficiently provide recommendations using songs with similar fingerprints to the one provided by the user. end users could be any of the following: music producers, hobbyist musicians, music theorists, audio engineers, music educators, or casual music listeners."

## Clarifications

### Session 2026-08-04

- Q: How should multi-channel (stereo or surround) audio snippets be processed during DSP feature extraction? → A: Convert multi-channel audio to mono by averaging channels prior to feature extraction.
- Q: Which mathematical downsampling statistic should be used to collapse each acoustic feature's time-series vector into a single scalar value for V1 fingerprints? → A: Arithmetic mean across all frames (producing 1 scalar per feature).
- Q: How should song identity and deduplication be determined to prevent duplicate feature records in the local relational database? → A: Use track ISRC (International Standard Recording Code) as the primary canonical deduplication key, falling back to the external platform track ID if ISRC is missing.

### Session 2026-08-03

- Q: How should song selection and confirmation work upon user input? → A: After user inputs a song name, system returns top 5 match results and asks user for confirmation before proceeding to feature engineering.
- Q: What structure does feature engineering follow? → A: Feature engineering is a composite step with multiple substeps computing individual acoustic features (such as spectral centroid and spectral flux) grouped into a single feature vector for the song.
- Q: What priority and behavior applies to DSP visualizations? → A: Lower-priority objective to visualize DSP attributes (e.g., spectrogram with highlighted spectral centroid and top contributing factors for spectral features).
- Q: What is the correct sequence of audio fetching vs fingerprinting? → A: System fetches online audio snippet first, then generates the fingerprint from the fetched audio snippet.
- Q: How can users interact with recommendations based on acoustic characteristics? → A: Users can modify acoustic characteristics of a song to receive recommendations matching the modified vector rather than the original song.
- Q: How are network interruptions handled during snippet fetching? → A: Retry up to 3 times with 5-second delays between attempts; if all 3 fail, display "network disconnected".
- Q: How are audio format support and audio processing errors handled? → A: Assume audio source is reliable for truncation/corruption, but if processing fails, display "audio file cannot be processed". System must support MP3, WAV, and FLAC formats.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Song Input to Stored Audio Fingerprint (Priority: P1)

As a user (music producer, hobbyist musician, audio engineer, music educator, music theorist, or casual listener), I want to input a song name, select from the top 5 matches, and confirm selection so that the system fetches an online audio snippet first, computes composite acoustic features, and stores the feature vector in a local database.

**Why this priority**: Core value of GenreGuru. Without searching matches, fetching audio snippets first, extracting composite DSP fingerprint features, and storing them locally, no downstream analysis or recommendation capability can function.

**Independent Test**: Can be tested independently by submitting a valid song name, confirming one of the top 5 matches, verifying online audio snippet retrieval first, validating composite feature extraction (`spectral_centroid`, `rms`, `spectral_bandwidth`, `spectral_contrast`, `spectral_flatness`, `spectral_rolloff`, `zero_crossing_rate`, and `mfcc`), and checking that the resulting feature vector is saved in the local relational database.

**Acceptance Scenarios**:

1. **Given** a valid song name provided by the user, **When** search is performed, **Then** the system presents the top 5 song match results and requests user confirmation. Upon confirmation, the system fetches the online audio snippet first, executes feature engineering substeps to compute acoustic features (`spectral_centroid`, `rms`, `spectral_bandwidth`, `spectral_contrast`, `spectral_flatness`, `spectral_rolloff`, `zero_crossing_rate`, and `mfcc` — explicitly omitting `spectral_flux`) grouped into a song feature vector, downsampling each feature time-vector into a single collapsed scalar value for V1, and saves the vector to the local relational database.
2. **Given** a song search query that returns no online matches, **When** processing is attempted, **Then** the system provides a clear error notification and does not create incomplete database records.
3. **Given** a song name that has already been fingerprinted and stored in the database, **When** the user submits the same song name again, **Then** the system detects the existing stored fingerprint and reuses stored data without duplicating entries.
4. **Given** a network interruption during audio snippet fetching, **When** fetching fails, **Then** the system retries fetching up to 3 times with a 5-second delay between attempts. If all 3 attempts fail, the system displays a "network disconnected" error.
5. **Given** a fetched audio snippet in MP3, WAV, or FLAC format, **When** digital signal processing cannot process the audio data, **Then** the system displays an "audio file cannot be processed" error.

---

### User Story 2 - Fingerprint Feature Retrieval & Inspection (Priority: P2)

As a music theorist, educator, or audio engineer, I want to view and inspect stored fingerprint feature metrics for any previously processed song so that I can understand and verify the digital audio characteristics of the track.

**Why this priority**: Allows domain experts and technical users to inspect extracted audio features, verifying data quality and understanding what numerical attributes represent the track's sonic profile before recommendation algorithms are built.

**Independent Test**: Can be tested independently by querying stored songs from the database and reading out the full set of extracted fingerprint feature fields.

**Acceptance Scenarios**:

1. **Given** a song whose fingerprint has been stored in the database, **When** a user requests feature details for that song, **Then** the system presents all stored feature components of the fingerprint in a structured, readable format.
2. **Given** multiple stored song fingerprints in the database, **When** a user lists stored catalog entries, **Then** the system returns a summary list of all available songs and their fingerprint metadata.

---

### User Story 3 - Digital Signal Processing Visualization (Priority: P3 - Low Priority)

As an audio engineer or music theorist, I want to view visual representations of DSP features (such as spectrograms with spectral centroid highlights and feature contribution factors) so that I can visually analyze the track's spectral breakdown.

**Why this priority**: Enhances analytical depth for technical users but is secondary to core fingerprint storage and recommendation functionality.

**Independent Test**: Can be tested by selecting a processed song and toggling visualization mode to verify spectrogram rendering and feature factor highlighting.

**Acceptance Scenarios**:

1. **Given** a fingerprinted song, **When** visualization is requested, **Then** the system displays the song spectrogram with highlighted spectral centroid and top contributing feature factors.

---

### User Story 4 - Custom Feature Vector Modification for Recommendations (Priority: P3 - Low Priority)

As a music producer or listener, I want to manually adjust acoustic feature sliders for a processed song so that recommendations are generated against my modified acoustic target rather than the original track.

**Why this priority**: Provides interactive creative control over recommendation queries beyond static song matching.

**Independent Test**: Can be tested by adjusting feature vector values on a song profile and verifying recommendation query results change accordingly.

**Acceptance Scenarios**:

1. **Given** a fingerprinted song profile, **When** the user modifies acoustic feature values, **Then** downstream recommendations return songs matching the modified feature vector.

---

### Edge Cases

- **Ambiguous Match Selection**: When user inputs a song name, system returns top 5 candidate matches and requires explicit user confirmation before fetching audio.
- **Network Interruption**: Temporary network failure during online audio snippet fetching triggers up to 3 retries spaced 5 seconds apart. If all fail, "network disconnected" error is displayed.
- **Audio File Reliability & Format Handling**: Audio snippets in MP3, WAV, or FLAC are supported. Multi-channel (stereo/surround) audio snippets are automatically downmixed to single-channel (mono) by averaging channels prior to processing. Truncation and corruption are assumed minimal from reliable sources, but if audio data cannot be processed by DSP algorithms, "audio file cannot be processed" error is displayed.
- **Silent or Non-Musical Content**: Non-musical or silent tracks produce valid feature vectors with zero/low energy metrics without failing DSP pipeline.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a song name input string, search online catalog sources, return top 5 matching candidates, and await user confirmation before initiating snippet fetching.
- **FR-002**: System MUST fetch an online audio snippet *first* (prior to feature extraction) for the user-confirmed song, supporting MP3, WAV, and FLAC audio formats.
- **FR-003**: System MUST execute a composite feature engineering pipeline computing acoustic features (`spectral_centroid`, `rms`, `spectral_bandwidth`, `spectral_contrast`, `spectral_flatness`, `spectral_rolloff`, `zero_crossing_rate`, and `mfcc`; explicitly omitting `spectral_flux`). Multi-channel (stereo/surround) audio snippets MUST be downmixed to single-channel (mono) by averaging channels prior to DSP extraction. In V1, each feature's time-vector MUST be downsampled (collapsed) into a single scalar value per feature by computing the arithmetic mean across all audio frames, while allowing future versions to retain temporal dimensions.
- **FR-004**: System MUST store extracted song fingerprint feature vectors into a local relational database with full data persistence.
- **FR-005**: System MUST associate each stored fingerprint record with song metadata, including song title, artist, track ISRC (if available), platform track ID, audio source reference, and processing timestamp.
- **FR-006**: System MUST prevent duplicate feature records when the same song is processed multiple times by enforcing uniqueness based primarily on track ISRC (International Standard Recording Code), falling back to external platform track ID if ISRC is missing or unavailable.
- **FR-007**: System MUST handle network interruptions during snippet fetching by retrying up to 3 times with 5-second delays between attempts; if all fail, display "network disconnected" error feedback.
- **FR-008**: System MUST display an "audio file cannot be processed" error if fetched MP3, WAV, or FLAC audio data fails digital signal processing.
- **FR-009**: System MUST allow users to query and retrieve existing fingerprint feature records from the local relational database.
- **FR-010**: System MAY (P3 lower priority) provide DSP visualization capabilities, showing song spectrograms with highlighted spectral centroid and feature contribution factors.
- **FR-011**: System MAY (P3 lower priority) allow users to modify acoustic feature vector values to retrieve recommendations matching the modified profile.

### Key Entities *(include if feature involves data)*

- **Song**: Represents a track identified primarily by track ISRC (International Standard Recording Code), falling back to platform track ID if ISRC is missing, along with title, artist, and source reference.
- **AudioSnippet**: Represents the fetched sample audio file/buffer in MP3, WAV, or FLAC format, including duration, sampling parameters, channel configuration (downmixed to mono for DSP), and retrieval status.
- **SongFingerprint**: Represents the composite set of numerical feature vectors extracted via digital signal processing (`spectral_centroid`, `rms`, `spectral_bandwidth`, `spectral_contrast`, `spectral_flatness`, `spectral_rolloff`, `zero_crossing_rate`, `mfcc`) downsampled to single scalar values (arithmetic mean across frames) for V1 and linked to a specific Song.
- **FeatureRecord**: The database table representation persisting the song fingerprint features, track ISRC (or platform track ID fallback), metadata, and timestamps in the local relational database with unique constraints on the primary identifier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of valid, mainstream song name queries successfully return top 5 matches, retrieve an online audio snippet, and complete fingerprint generation without errors.
- **SC-002**: Audio fingerprint feature extraction completes within 10 seconds per audio snippet on standard consumer hardware.
- **SC-003**: 100% of generated song fingerprints are correctly persisted with complete composite feature vectors in the local relational database without data loss.
- **SC-004**: Users across all target roles can initiate a song fingerprinting run by providing a song name and confirming one of the top 5 results.
- **SC-005**: Database queries for existing stored song fingerprints return results in under 500 milliseconds.

## Assumptions

- Target users have an active internet connection required to fetch online song snippets.
- Online audio fetching currently utilizes publicly accessible, user-independent audio preview snippets in MP3, WAV, or FLAC formats via Deezer API.
- Future versions may introduce user authentication (e.g., via `deezer-python`) to access personal user libraries on Deezer, Spotify, YouTube Music, Apple Music, Amazon Music, etc.
- Audio source is assumed reliable regarding file truncation/corruption; unprocessable audio displays explicit error.
- The local relational database is initialized and accessible on the local system environment.
- Downstream recommendation algorithms will be implemented in subsequent project phases using the stored fingerprint data.
