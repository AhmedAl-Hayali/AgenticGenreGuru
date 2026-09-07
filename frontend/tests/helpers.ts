// Shared infrastructure for the frontend contract tests. Mirrors the id
// contract in fingerprint_app/partials/*.html: index-page.ts requires every id
// via requireById(); if one drops out of the markup, bootstrap throws and all
// tests fail as a hard error.

import { expect, vi } from "vitest";
import type { ApiConfig, Match, ConfirmResponse } from "../fingerprint_app/ts/dto.ts";
import { clearCookies } from "./setup.ts";

export const CONFIG: ApiConfig = {
  searchPattern: "/api/search/",
  confirmUrl: "/api/confirm/",
  featureLabels: {
    spectral_centroid: "Spectral Centroid (Hz)",
    rms: "RMS",
    spectral_bandwidth: "Spectral Bandwidth (Hz)",
    spectral_contrast: "Spectral Contrast (dB)",
    spectral_flatness: "Spectral Flatness",
    spectral_rolloff: "Spectral Rolloff (Hz)",
    zero_crossing_rate: "Zero Crossing Rate",
    mfcc: "MFCC",
  },
};

export const MATCH: Match = {
  deezer_id: 3135556,
  title: "Harder, Better, Faster, Stronger",
  isrc: "GBDUW0000059",
  duration: 226,
  preview: "https://example.test/preview.mp3",
  artist: { id: 27, name: "Daft Punk" },
  album: { id: 302127, title: "Discovery" },
};

export const CONFIRM_OK: ConfirmResponse = {
  status: "success",
  song_id: "11111111-1111-1111-1111-111111111111",
  deezer_id: MATCH.deezer_id,
  isrc: MATCH.isrc,
  fingerprint: {
    spectral_centroid: 2500.5,
    rms: 0.21,
    vector_length: 13,
  },
};

export function fixtureHtml(cfg: ApiConfig): string {
  // Mirrors the id contract in fingerprint_app/partials/*.html.
  // index-page.ts requires every id via requireById(); if one drops out of
  // the markup, bootstrap throws here and all tests fail as a hard error.
  return `
    <form id="search-form" autocomplete="off">
      <input id="query" name="query">
      <button id="search-btn" type="submit">Search</button>
    </form>
    <p id="status" aria-live="polite"></p>
    <ul id="candidates"></ul>
    <section id="result-section" class="panel hidden">
      <p id="result-title"></p>
      <dl id="result"></dl>
    </section>
    <script id="api-config" type="application/json">${JSON.stringify(cfg)}</script>
`;
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export async function bootApp({
  config = CONFIG,
  cookie = "csrftoken=token123",
}: { config?: ApiConfig; cookie?: string | null } = {}) {
  document.body.innerHTML = fixtureHtml(config);
  // jsdom keeps one cookie jar for the whole test file, so reset it each boot.
  clearCookies();
  if (cookie) document.cookie = cookie + "; path=/";

  const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: "success", matches: [] }));
  vi.stubGlobal("fetch", fetchMock);

  vi.resetModules();
  await import("../fingerprint_app/ts/pages/index-page.ts");

  return {
    fetchMock,
    form: document.getElementById("search-form") as HTMLFormElement,
    query: document.getElementById("query") as HTMLInputElement,
    searchButton: document.getElementById("search-btn") as HTMLButtonElement,
    status: document.getElementById("status") as HTMLElement,
    candidates: document.getElementById("candidates") as HTMLUListElement,
    resultSection: document.getElementById("result-section") as HTMLElement,
    resultTitle: document.getElementById("result-title") as HTMLElement,
    result: document.getElementById("result") as HTMLElement,
  };
}

export type BootEls = Awaited<ReturnType<typeof bootApp>>;

export function submitSearch(els: BootEls, query = "Daft Punk") {
  els.query.value = query;
  els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
}

export async function waitForCandidate(els: BootEls) {
  await vi.waitFor(() => {
    expect(els.candidates.children.length).toBe(1);
  });
}

export function findConfirmCall(
  fetchMock: BootEls["fetchMock"],
): [string, RequestInit] | undefined {
  const call = fetchMock.mock.calls.find(([url]) => String(url).includes("/api/confirm/"));
  return call ? [String(call[0]), call[1] as RequestInit] : undefined;
}

/** Grab the first rendered candidate row, throwing if none exists. */
export function grabCandidate(els: BootEls): HTMLElement {
  const el = els.candidates.firstElementChild as HTMLElement | null;
  if (!el) {
    throw new Error("Expected a candidate row to be rendered.");
  }
  return el;
}
