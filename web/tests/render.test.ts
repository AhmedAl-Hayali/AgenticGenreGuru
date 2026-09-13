// Unit tests for the render module (fingerprint_app/ts/render.ts).
// renderCandidates: structural contract of the candidate list — item shape,
// full contributor roster + lazy cover rendering, and click/keyboard delegation.
// renderFingerprint: the formatting edge cases and the missing-featureLabels
// fail-loud guard. The candidate artists overflow ("scroll reveal") interaction
// lives in its own module and test (scroll-reveal.test.ts).

import { describe, expect, it, vi } from "vitest";
import type { ConfirmResponse, Match } from "../fingerprint_app/ts/dto.ts";
import {
  renderCandidates,
  renderFingerprint,
  type PreviewControl,
} from "../fingerprint_app/ts/render.ts";
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

function renderInto(
  matches: Match[],
  {
    onCandidateClick = () => {},
    onCandidatePreview = () => {},
  }: { onCandidateClick?: () => void; onCandidatePreview?: () => void } = {},
) {
  const list = document.createElement("ul");
  list.dataset.providerIcon = PROVIDER_ICON;
  list.dataset.providerName = "Deezer";
  renderCandidates(list, matches, { onCandidateClick, onCandidatePreview });
  return { list };
}

describe("renderCandidates", () => {
  it("renders one item per match in order: cover, then body with title-row, artists, and playback", () => {
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
    expect(bodyChildren[2]?.classList.contains("candidate-playback")).toBe(true);

    const provider = titleRow?.querySelector(".candidate-provider");
    expect(provider?.getAttribute("src")).toBe(PROVIDER_ICON);
    expect(provider?.getAttribute("alt")).toBe("Deezer");
    expect(provider?.hasAttribute("tabindex")).toBe(false);

    expect(titleRow?.querySelector(".candidate-preview")).toBeNull();
  });

  it("lays out the preview button and progress bar in a shared playback row", () => {
    const { list } = renderInto([MATCH]);

    const playback = list.querySelector(".candidate-playback");
    expect(playback).not.toBeNull();

    const playbackChildren = Array.from(playback!.children);
    expect(playbackChildren[0]?.classList.contains("candidate-preview")).toBe(true);
    expect(playbackChildren[1]?.classList.contains("candidate-progress")).toBe(true);

    const button = playbackChildren[0];
    expect(button?.tagName).toBe("BUTTON");
    expect(button?.getAttribute("type")).toBe("button");
    expect(button?.getAttribute("aria-label")).toBe(`Preview "${MATCH.title}"`);
    expect(button?.hasAttribute("tabindex")).toBe(false);

    const gauge = playbackChildren[1];
    expect(gauge?.getAttribute("role")).toBe("progressbar");
    expect(gauge?.getAttribute("aria-valuemin")).toBe("0");
    expect(gauge?.getAttribute("aria-valuemax")).toBe("100");
    expect(gauge?.getAttribute("aria-valuenow")).toBe("0");
    expect(playback?.querySelector(".candidate-progress-fill")).not.toBeNull();
  });

  it("omits the provider icon when the list carries no provider data", () => {
    const list = document.createElement("ul");
    renderCandidates(list, [MATCH], { onCandidateClick: () => {}, onCandidatePreview: () => {} });

    expect(list.querySelector(".candidate-provider")).toBeNull();
  });

  it("disables the preview button when the match has no preview", () => {
    const { list } = renderInto([{ ...MATCH, preview: "" }]);

    const preview = list.querySelector(".candidate-preview") as HTMLButtonElement;
    expect(preview.disabled).toBe(true);
    expect(preview.getAttribute("aria-label")).toBe("No preview available for this song.");
    expect(preview.getAttribute("title")).toBe("No preview available for this song.");
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
    const { list } = renderInto([MATCH], { onCandidateClick: handler });

    const item = list.children[0] as HTMLElement;
    item.click();

    expect(handler).toHaveBeenCalledWith(MATCH, item);
  });

  it("delegates preview activation with the match, the button, and the gauge", () => {
    const handler = vi.fn();
    const { list } = renderInto([MATCH], { onCandidatePreview: handler });

    const button = list.querySelector(".candidate-preview") as HTMLButtonElement;
    button.click();

    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler.mock.calls[0]![0]).toBe(MATCH);
    const control = handler.mock.calls[0]![1] as PreviewControl;
    expect(control.button).toBe(button);
    expect(control.gauge.classList.contains("candidate-progress")).toBe(true);
  });

  it("does not treat a preview button activation as a row activation", () => {
    const clickHandler = vi.fn();
    const previewHandler = vi.fn();
    const { list } = renderInto([MATCH], {
      onCandidateClick: clickHandler,
      onCandidatePreview: previewHandler,
    });
    const item = list.children[0] as HTMLElement;
    const button = item.querySelector(".candidate-preview") as HTMLButtonElement;

    button.click();
    expect(clickHandler).not.toHaveBeenCalled();
    expect(previewHandler).toHaveBeenCalledTimes(1);
  });

  it("keeps row activation working from the cover while ignoring the preview button", () => {
    const clickHandler = vi.fn();
    const previewHandler = vi.fn();
    const { list } = renderInto([MATCH], {
      onCandidateClick: clickHandler,
      onCandidatePreview: previewHandler,
    });
    const item = list.children[0] as HTMLElement;
    const cover = item.querySelector(".candidate-cover") as HTMLElement;

    cover.click();
    expect(clickHandler).toHaveBeenCalledWith(MATCH, item);
    expect(previewHandler).not.toHaveBeenCalled();
  });

  it("activates on Enter and Space, preventing the key's default", () => {
    const handler = vi.fn();
    const { list } = renderInto([MATCH], { onCandidateClick: handler });
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

  it("does not activate the row from keys pressed on the preview button", () => {
    const clickHandler = vi.fn();
    const previewHandler = vi.fn();
    const { list } = renderInto([MATCH], {
      onCandidateClick: clickHandler,
      onCandidatePreview: previewHandler,
    });
    const item = list.children[0] as HTMLElement;
    const button = item.querySelector(".candidate-preview") as HTMLButtonElement;

    const enter = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    const space = new KeyboardEvent("keydown", { key: " ", bubbles: true, cancelable: true });
    button.dispatchEvent(enter);
    button.dispatchEvent(space);

    expect(clickHandler).not.toHaveBeenCalled();
    expect(previewHandler).not.toHaveBeenCalled();
    expect(item.classList.contains("selected")).toBe(false);
  });

  it("ignores keys other than Enter or Space", () => {
    const handler = vi.fn();
    const { list } = renderInto([MATCH], { onCandidateClick: handler });
    const item = list.children[0] as HTMLElement;

    const tab = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    const tabDefault = vi.spyOn(tab, "preventDefault");
    item.dispatchEvent(tab);

    expect(handler).not.toHaveBeenCalled();
    expect(tabDefault).not.toHaveBeenCalled();
  });

  it("replaces previously rendered candidates on re-render", () => {
    const { list } = renderInto([MATCH]);

    renderCandidates(list, [MATCH, MINIMAL_MATCH], {
      onCandidateClick: () => {},
      onCandidatePreview: () => {},
    });

    expect(list.children).toHaveLength(2);
  });

  it("keeps one row tab stop plus one preview button stop per candidate", () => {
    const five = [MATCH, MATCH, MATCH, MATCH, MATCH];
    const { list } = renderInto(five);

    const rowStops = Array.from(list.querySelectorAll(".candidate[tabindex]"));
    expect(rowStops).toHaveLength(5);

    const previewButtons = Array.from(list.querySelectorAll(".candidate-preview"));
    expect(previewButtons).toHaveLength(5);
    for (const button of previewButtons) {
      expect(button.hasAttribute("tabindex")).toBe(false);
    }

    const gauges = Array.from(list.querySelectorAll(".candidate-progress"));
    expect(gauges).toHaveLength(5);
    for (const gauge of gauges) {
      expect(gauge.hasAttribute("tabindex")).toBe(false);
    }

    const selectors = list.querySelectorAll("button, [tabindex]");
    expect(selectors).toHaveLength(10);
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
