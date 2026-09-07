// Unit tests for the render module (fingerprint_app/ts/render.ts).
// renderCandidates: structural contract of the candidate list — item shape,
// label composition, and click/keyboard delegation. renderFingerprint: the
// formatting edge cases and the missing-featureLabels fail-loud guard.

import { describe, expect, it, vi } from "vitest";
import type { ConfirmResponse, Match } from "../fingerprint_app/ts/dto.ts";
import { renderCandidates, renderFingerprint } from "../fingerprint_app/ts/render.ts";
import { CONFIRM_OK, MATCH } from "./helpers.ts";

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

const MINIMAL_MATCH: Match = {
  deezer_id: 1001,
  title: "Around the World",
  isrc: "GBDUW0000123",
  duration: 217,
  preview: "https://example.test/preview-minimal.mp3",
};

function renderInto(matches: Match[], handler = () => {}) {
  const list = document.createElement("ul");
  renderCandidates(list, matches, handler);
  return { list };
}

describe("renderCandidates", () => {
  it("renders one item per match in order, badge before the label", () => {
    const { list } = renderInto([MATCH, MINIMAL_MATCH]);

    const items = Array.from(list.children);
    expect(items).toHaveLength(2);

    const first = items[0] as HTMLElement;
    const badge = first.firstElementChild;
    expect(badge?.classList.contains("badge")).toBe(true);
    expect(badge?.textContent).toBe("Selected");
    expect(badge?.nextElementSibling?.classList.contains("title")).toBe(true);
  });

  it("labels a match as 'title · artist' with the album in parentheses", () => {
    const { list } = renderInto([MATCH]);

    const label = (list.children[0] as HTMLElement).querySelector(".title")?.textContent ?? "";
    expect(label).toContain("Harder, Better, Faster, Stronger · Daft Punk");
    expect(label).toContain("(Discovery)");
  });

  it("falls back to 'Unknown artist' and omits album meta when absent", () => {
    const { list } = renderInto([MINIMAL_MATCH]);

    const label = (list.children[0] as HTMLElement).querySelector(".title")?.textContent ?? "";
    expect(label).toContain("Unknown artist");
    expect(label).not.toContain("(");
  });

  it("starts each item unselected with a button role and zero tabindex", () => {
    const { list } = renderInto([MATCH]);

    const item = list.children[0] as HTMLElement;
    expect(item.getAttribute("role")).toBe("button");
    expect(item.tabIndex).toBe(0);
    expect(item.getAttribute("aria-pressed")).toBe("false");
    expect(item.classList.contains("selected")).toBe(false);
  });

  it("delegates clicks with the match and the list item", () => {
    const handler = vi.fn();
    const { list } = renderInto([MATCH], handler);

    const item = list.children[0] as HTMLElement;
    item.click();

    expect(handler).toHaveBeenCalledWith(MATCH, item);
  });

  it("activates on Enter and Space, preventing the key's default", () => {
    const handler = vi.fn();
    const { list } = renderInto([MATCH], handler);
    const item = list.children[0] as HTMLElement;

    const enter = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    const enterDefault = vi.spyOn(enter, "preventDefault");
    item.dispatchEvent(enter);
    expect(handler).toHaveBeenCalledWith(MATCH, item);
    expect(enterDefault).toHaveBeenCalled();

    const space = new KeyboardEvent("keydown", { key: " ", bubbles: true, cancelable: true });
    const spaceDefault = vi.spyOn(space, "preventDefault");
    item.dispatchEvent(space);
    expect(handler).toHaveBeenCalled();
    expect(spaceDefault).toHaveBeenCalled();
  });

  it("ignores keys other than Enter or Space", () => {
    const handler = vi.fn();
    const { list } = renderInto([MATCH], handler);
    const item = list.children[0] as HTMLElement;

    const tab = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    const tabDefault = vi.spyOn(tab, "preventDefault");
    item.dispatchEvent(tab);

    expect(handler).not.toHaveBeenCalled();
    expect(tabDefault).not.toHaveBeenCalled();
  });

  it("replaces previously rendered candidates on re-render", () => {
    const { list } = renderInto([MATCH]);

    renderCandidates(list, [MATCH, MINIMAL_MATCH], () => {});

    expect(list.children).toHaveLength(2);
  });
});

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

  it("renders the standard rows with mapped feature labels and vector length", () => {
    const section = document.createElement("section");
    const title = document.createElement("p");
    const result = document.createElement("dl");

    renderFingerprint(section, title, result, BODY, {
      spectral_centroid: "Spectral Centroid (Hz)",
    });

    const text = result.textContent ?? "";
    expect(text).toContain("Song ID");
    expect(text).toContain(BODY.song_id);
    expect(text).toContain("Deezer ID");
    expect(text).toContain(BODY.isrc);
    expect(text).toContain("Spectral Centroid (Hz)");
    expect(text).toContain("Vector Length");
    expect(text).toContain("13");
  });

  it("renders dashes when the body carries no fingerprint", () => {
    const section = document.createElement("section");
    const title = document.createElement("p");
    const result = document.createElement("dl");
    const noFingerprint = { ...BODY, fingerprint: undefined } as ConfirmResponse;

    renderFingerprint(section, title, result, noFingerprint, {});

    expect(result.textContent).toContain("—");
    expect(result.textContent).not.toContain("2500.5234");
  });

  it("throws a TypeError when featureLabels is missing", () => {
    const section = document.createElement("section");
    section.classList.add("hidden");
    const title = document.createElement("p");
    const result = document.createElement("dl");

    expect(() => renderFingerprint(section, title, result, CONFIRM_OK, undefined)).toThrow(
      "featureLabels is required to render a fingerprint.",
    );
    expect(section.classList.contains("hidden")).toBe(true);
    expect(result.textContent).toBe("");
  });
});
