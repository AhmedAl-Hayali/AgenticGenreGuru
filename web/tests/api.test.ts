// Unit tests for the API-layer module (fingerprint_app/ts/api.ts): request
// shaping (URL encoding, confirm payload/CSRF), the abortable timeout wrapper,
// and the defensive JSON body reader. The controller-level reachability/error
// mappings these helpers feed into live in page-controller.test.ts.

import { describe, expect, it, vi } from "vitest";
import {
  confirmTrack,
  fetchWithTimeout,
  getCsrfToken,
  readJsonMaybe,
  searchTracks,
} from "../fingerprint_app/ts/api.ts";
import { clearCookies } from "./setup.ts";
import { CONFIG, MATCH, jsonResponse } from "./helpers.ts";

describe("searchTracks", () => {
  it("encodes the query and targets the configured search pattern", () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response());
    vi.stubGlobal("fetch", fetchMock);

    searchTracks(CONFIG, "Daft Punk");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/search/?query=Daft%20Punk",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });
});

describe("confirmTrack", () => {
  function stubFetch() {
    const fetchMock = vi.fn().mockResolvedValue(new Response());
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("POSTs the match fields with JSON content type and the CSRF token", () => {
    clearCookies();
    document.cookie = "csrftoken=token123; path=/";
    const fetchMock = stubFetch();

    confirmTrack(CONFIG, MATCH);

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/confirm/");
    expect(options.method).toBe("POST");
    expect((options.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect((options.headers as Record<string, string>)["X-CSRFToken"]).toBe("token123");
    expect(JSON.parse(String(options.body))).toEqual({
      deezer_id: MATCH.deezer_id,
      title: MATCH.title,
      isrc: MATCH.isrc,
      duration: MATCH.duration,
      preview: MATCH.preview,
      artists: MATCH.artists,
      album: MATCH.album,
    });
  });

  it("sends an empty CSRF token when no cookie is set", () => {
    clearCookies();
    const fetchMock = stubFetch();

    confirmTrack(CONFIG, MATCH);

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((options.headers as Record<string, string>)["X-CSRFToken"]).toBe("");
  });
});

describe("fetchWithTimeout", () => {
  it("aborts the fetch signal once the timeout elapses", async () => {
    vi.useFakeTimers();
    let signal: AbortSignal | null | undefined;
    const fetchMock = vi.fn((_url: RequestInfo, options: RequestInit) => {
      signal = options.signal;
      return new Promise<Response>(() => {});
    });
    vi.stubGlobal("fetch", fetchMock);

    fetchWithTimeout("https://example.test/", {}, 1000);
    expect(signal?.aborted).toBe(false);

    await vi.advanceTimersByTimeAsync(1000);
    expect(signal?.aborted).toBe(true);
    vi.useRealTimers();
  });

  it("clears the cancel timer when the request settles early", async () => {
    vi.useFakeTimers();
    let signal: AbortSignal | null | undefined;
    const body = jsonResponse({ status: "success", matches: [] });
    const fetchMock = vi.fn((_url: RequestInfo, options: RequestInit) => {
      signal = options.signal;
      return Promise.resolve(body);
    });
    vi.stubGlobal("fetch", fetchMock);

    const pending = fetchWithTimeout("https://example.test/", {}, 1000);
    const response = await pending;
    expect(response).toBe(body);

    await vi.advanceTimersByTimeAsync(5000);
    expect(signal?.aborted).toBe(false);
    vi.useRealTimers();
  });
});

describe("readJsonMaybe", () => {
  it("parses a well-formed JSON body", async () => {
    const response = jsonResponse({ status: "success" });

    await expect(readJsonMaybe(response)).resolves.toEqual({ status: "success" });
  });

  it("returns an empty object for a malformed body", async () => {
    const response = new Response("<not json>", { status: 200 });

    await expect(readJsonMaybe(response)).resolves.toEqual({});
  });
});

describe("getCsrfToken", () => {
  it("reads and decodes the csrftoken cookie", () => {
    clearCookies();
    document.cookie = "csrftoken=token123; path=/";

    expect(getCsrfToken(document)).toBe("token123");
  });

  it("returns an empty string when the cookie is absent", () => {
    clearCookies();

    expect(getCsrfToken(document)).toBe("");
  });
});
