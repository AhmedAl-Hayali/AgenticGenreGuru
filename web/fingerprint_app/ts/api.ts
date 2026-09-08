import type { ApiConfig, Match } from "./dto.ts";

export const REQUEST_TIMEOUT_MS = 15000;

const MATCH_FIELDS = [
  "deezer_id",
  "title",
  "isrc",
  "duration",
  "preview",
  "artist",
  "album",
] as const satisfies ReadonlyArray<keyof Match>;

/** `fetch` with an `AbortController` that fires after `timeoutMs`; timer cleared on settle. */
export function fetchWithTimeout(url: string, options: RequestInit, timeoutMs: number) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() => {
    clearTimeout(timer);
  });
}

/**
 * Parse a JSON response body. Returns `Partial<T>` on success, or an
 * empty object if the body is malformed or the parse throws.
 */
export function readJsonMaybe<T = Record<string, unknown>>(
  response: Response,
): Promise<Partial<T>> {
  return response.json().catch(() => ({}));
}

/** GET the search API with the given query. Returns the raw `Response`; caller handles errors. */
export function searchTracks(config: ApiConfig, query: string) {
  return fetchWithTimeout(
    `${config.searchPattern}?query=${encodeURIComponent(query)}`,
    {},
    REQUEST_TIMEOUT_MS,
  );
}

/**
 * POST a filtered match payload to the confirm endpoint. The CSRF
 * token is read from the `csrftoken` cookie automatically.
 */
export function confirmTrack(config: ApiConfig, match: Match) {
  const payload = Object.fromEntries(MATCH_FIELDS.map((key) => [key, match[key]]));

  return fetchWithTimeout(
    config.confirmUrl,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    },
    REQUEST_TIMEOUT_MS,
  );
}

/** Django CSRF token from `document`, or `""` if the cookie is absent. */
export function getCsrfToken(doc: Document = document) {
  const match = doc.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1] ?? "") : "";
}
