// Unit tests for renderFingerprint's formatting edge cases: a null feature
// label falls back to the feature key, non-number feature values pass through
// verbatim, and non-integer numbers are clamped to four decimals.

import { describe, expect, it } from "vitest";
import type { ConfirmResponse } from "../fingerprint_app/ts/dto.ts";
import { renderFingerprint } from "../fingerprint_app/ts/render.ts";

const BODY = {
  status: "success",
  song_id: "11111111-1111-1111-1111-111111111111",
  deezer_id: 3135556,
  isrc: "GBDUW0000059",
  fingerprint: {
    spectral_centroid: 2500.5234,
    rms: "high",
    vector_length: 13,
  },
} as ConfirmResponse;

describe("renderFingerprint formatting", () => {
  it("falls back to the feature key for a null label", () => {
    const section = document.createElement("section");
    const title = document.createElement("p");
    const result = document.createElement("dl");
    const featureLabels = {
      spectral_centroid: "Spectral Centroid",
      rms: null,
    } as unknown as Record<string, string>;

    renderFingerprint(section, title, result, BODY, featureLabels);

    const terms = Array.from(result.querySelectorAll("dt")).map((dt) => dt.textContent);
    expect(terms).toContain("rms");
    expect(terms).toContain("Spectral Centroid");
  });

  it("passes non-number values through verbatim", () => {
    const section = document.createElement("section");
    const title = document.createElement("p");
    const result = document.createElement("dl");
    const featureLabels = { rms: "RMS" };

    renderFingerprint(section, title, result, BODY, featureLabels);

    expect(result.textContent).toContain("high");
  });

  it("formats non-integer numbers to four decimals", () => {
    const section = document.createElement("section");
    const title = document.createElement("p");
    const result = document.createElement("dl");
    const featureLabels = { spectral_centroid: "Spectral Centroid" };

    renderFingerprint(section, title, result, BODY, featureLabels);

    expect(result.textContent).toContain("2500.5234");
  });

  it("shows the default title when the body carries no title", () => {
    const section = document.createElement("section");
    const title = document.createElement("p");
    const result = document.createElement("dl");

    renderFingerprint(section, title, result, BODY, {});

    expect(section.classList.contains("hidden")).toBe(false);
    expect(title.textContent).toBe("Fingerprint stored");
  });

  it("renders integer feature values without decimals", () => {
    const section = document.createElement("section");
    const title = document.createElement("p");
    const result = document.createElement("dl");
    const integerBody = {
      ...BODY,
      fingerprint: { spectral_centroid: 13 },
    } as ConfirmResponse;

    renderFingerprint(section, title, result, integerBody, {
      spectral_centroid: "Spectral Centroid",
    });

    expect(result.textContent).toContain("13");
  });
});
