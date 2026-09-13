// Unit tests for the render module (fingerprint_app/ts/render.ts).
// renderCandidates: structural contract of the candidate list — item shape,
// full contributor roster + lazy cover rendering, and click/keyboard delegation.
// renderFingerprint: the formatting edge cases and the missing-featureLabels
// fail-loud guard. The candidate artists overflow ("scroll reveal") interaction
// lives in its own module and test (scroll-reveal.test.ts).

import { describe, expect, it, vi } from "vitest";
import type { ConfirmResponse, Match } from "../fingerprint_app/ts/dto.ts";
import { renderCandidates, renderFingerprint } from "../fingerprint_app/ts/render.ts";
import { CONFIRM_OK, MATCH } from "./helpers.ts";
import { CONFIRM_OK, MATCH, MINIMAL_MATCH } from "./helpers.ts";
import { installIntersectionObserver } from "./setup.ts";

const BODY = {
  song_id: "11111111-1111-1111-1111-111111111111",
  deezer_id: 3135556,
  isrc: "GBDUW0000059",
  fingerprint: {
    spectral_centroid: 2500.5234,
    rms: "high",
    vector_length: 13,
  },
} as ConfirmResponse;

const PROVIDER_ICON = "/static/fingerprint_app/images/deezer-heart.png";

function renderInto(matches: Match[], handler = () => {}) {
  const list = document.createElement("ul");
  list.dataset.providerIcon = PROVIDER_ICON;
  list.dataset.providerName = "Deezer";
  renderCandidates(list, matches, handler);
  return { list };
}

describe("renderCandidates", () => {
  it("renders one item per match in order: cover, then body with title-row above artists", () => {
    const { list } = renderInto([MATCH, MINIMAL_MATCH]);

    const items = Array.from(list.children);
    expect(items).toHaveLength(2);

    const children = Array.from(items[0]!.children);
    expect(children[0]?.classList.contains("candidate-cover")).toBe(true);
    expect(children[1]?.classList.contains("candidate-body")).toBe(true);

    const bodyChildren = Array.from(children[1]!.children);
    const titleRow = bodyChildren[0];
    expect(titleRow?.classList.contains("candidate-title-row")).toBe(true);
    expect(bodyChildren[1]?.classList.contains("candidate-artists")).toBe(true);

    const provider = titleRow?.querySelector(".candidate-provider");
    expect(provider?.getAttribute("src")).toBe(PROVIDER_ICON);
    expect(provider?.getAttribute("alt")).toBe("Deezer");
    expect(provider?.hasAttribute("tabindex")).toBe(false);
  });

  it("omits the provider icon when the list carries no provider data", () => {
    const list = document.createElement("ul");
    renderCandidates(list, [MATCH], () => {});

    expect(list.querySelector(".candidate-provider")).toBeNull();
  });

  it("renders the title, album meta, and the full contributor roster", () => {
    const { list } = renderInto([MATCH]);

    const item = list.children[0] as HTMLElement;
    const titleRow = item.querySelector(".candidate-title-row");
    expect(titleRow?.querySelector(".candidate-title")?.textContent).toBe(MATCH.title);
    expect(titleRow?.querySelector(".candidate-meta")?.textContent).toBe("(Discovery)");
    expect(titleRow?.querySelector(".candidate-artists")).toBeNull();

    const artistNames = Array.from(item.querySelectorAll(".candidate-artist")).map(
      (el) => el.textContent,
    );
    expect(artistNames).toEqual(["Daft Punk", "Stardust"]);
    const artists = item.querySelector(".candidate-artists");
    expect(artists?.getAttribute("title")).toBe("Daft Punk, Stardust");
  });

  it("shows the overflowing fade hint on every contributor line", () => {
    const { list } = renderInto([MATCH]);

    const fade = list.querySelector(".candidate-artists-fade");
    expect(fade?.textContent).toBe("…");
    expect(fade?.getAttribute("aria-hidden")).toBe("true");
  });

  it("falls back to 'Unknown artist' and omits album meta when absent", () => {
    const { list } = renderInto([MINIMAL_MATCH]);

    const item = list.children[0] as HTMLElement;
    expect(item.querySelector(".candidate-artist")?.textContent).toBe("Unknown artist");
    expect(item.querySelector(".candidate-artists")?.getAttribute("title")).toBe("Unknown artist");
    expect(item.querySelector(".candidate-meta")).toBeNull();
  });

  it("defers the cover src to data-src until the item is revealed", () => {
    const { list } = renderInto([MATCH]);

    const cover = list.querySelector(".candidate-cover") as HTMLImageElement;
    expect(cover.dataset.src).toBe("https://example.test/cover.jpg");
    expect(cover.hasAttribute("src")).toBe(false);
    expect(cover.getAttribute("alt")).toBe(MATCH.title);
    expect(cover.classList.contains("hidden")).toBe(false);
  });

  it("wires lazy cover loading: observes rows whose covers have a pending data-src", () => {
    const handles = installIntersectionObserver();
    renderInto([MATCH, MINIMAL_MATCH]);

    const observer = handles[0]!;
    expect(observer.observed).toHaveLength(1);
    expect(observer.observed[0]?.querySelector(".candidate-cover")?.getAttribute("data-src")).toBe(
      "https://example.test/cover.jpg",
    );
  });

  it("hides the cover when no cover is available and never observes it", () => {
    const handles = installIntersectionObserver();
    const { list } = renderInto([{ ...MATCH, cover: "" }]);
    const observer = handles[0]!;

    const cover = list.querySelector(".candidate-cover");
    expect(cover?.classList.contains("hidden")).toBe(true);
    expect(cover?.hasAttribute("src")).toBe(false);
    expect(observer.observed).toEqual([]);
  });

  it("hides the cover when the image fails to load after being revealed", () => {
    const handles = installIntersectionObserver();
    const { list } = renderInto([MATCH]);
    const observer = handles[0]!;
    const item = list.children[0] as HTMLLIElement;
    const cover = item.querySelector(".candidate-cover") as HTMLImageElement;

    observer.trigger([{ target: item, isIntersecting: true }]);
    cover.dispatchEvent(new Event("error"));
    expect(cover.classList.contains("hidden")).toBe(true);
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

  it("keeps exactly one tab stop per candidate, never the scroll-reveal container", () => {
    const five = [MATCH, MATCH, MATCH, MATCH, MATCH];
    const { list } = renderInto(five);

    const tabStops = Array.from(list.querySelectorAll("[tabindex]"));
    expect(tabStops).toHaveLength(5);
    for (const stop of tabStops) {
      expect(stop.classList.contains("candidate")).toBe(true);
    }
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
