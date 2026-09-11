/** Application configuration served from the `#api-config` JSON blob. */
export interface ApiConfig {
  searchPattern: string;
  confirmUrl: string;
  featureLabels?: Record<string, string>;
}

/** A Deezer artist (id + display name). */
export interface Artist {
  id: number;
  name: string;
}

/** A Deezer album (id + title). */
export interface Album {
  id: number;
  title: string;
}

/** A single search-result candidate returned by the search API. */
export interface Match {
  deezer_id: number;
  title: string;
  isrc: string;
  duration: number;
  preview: string;
  artists: Artist[];
  album: Album | null;
  cover: string;
}

/** Envelope returned by the search endpoint. */
export interface SearchResponse {
  status?: string;
  error?: string;
  matches?: Match[];
}

/** Envelope returned by the confirm endpoint. */
export interface ConfirmResponse {
  status?: string;
  error?: string;
  title?: string;
  song_id?: string;
  deezer_id?: number;
  isrc?: string;
  fingerprint?: Record<string, unknown>;
}
