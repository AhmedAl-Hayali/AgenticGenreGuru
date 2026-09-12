// Unit tests for the scroll-reveal module (fingerprint_app/ts/scroll-reveal.ts).
// computeScrollDistance: the overflow math. bindScrollReveal: the generic
// clip-and-reveal binding for any inline track (measured via redefined
// clientWidth/scrollWidth, so the layout-independent behavior stays
// unit-testable).

import { describe, expect, it } from "vitest";
import { bindScrollReveal, computeScrollDistance } from "../fingerprint_app/ts/scroll-reveal.ts";

describe("computeScrollDistance", () => {
  it("returns a positive offset only when the content overflows", () => {
    expect(computeScrollDistance(100, 300)).toBe(200);
    expect(computeScrollDistance(100, 100)).toBe(0);
    expect(computeScrollDistance(300, 100)).toBe(0);
  });
});

describe("bindScrollReveal", () => {
  function makeOverflowingReveal({ viewport, track }: { viewport: number; track: number }) {
    const container = document.createElement("div");
    container.className = "candidate-artists";
    const trackEl = document.createElement("span");
    trackEl.className = "candidate-artists-track";
    container.appendChild(trackEl);
    const owner = document.createElement("li");
    owner.className = "candidate";
    owner.appendChild(container);
    Object.defineProperty(container, "clientWidth", {
      configurable: true,
      value: viewport,
    });
    Object.defineProperty(trackEl, "scrollWidth", { configurable: true, value: track });
    bindScrollReveal(container, owner);
    return { container, owner, track: trackEl };
  }

  it("no-ops when the track element is missing", () => {
    const container = document.createElement("div");
    container.className = "candidate-artists";

    expect(() => bindScrollReveal(container)).not.toThrow();
  });

  it("accepts a custom track selector", () => {
    const container = document.createElement("div");
    container.className = "candidate-title";
    const owner = document.createElement("li");
    const track = document.createElement("span");
    track.className = "candidate-title-track";
    container.appendChild(track);
    owner.appendChild(container);
    Object.defineProperty(container, "clientWidth", { configurable: true, value: 60 });
    Object.defineProperty(track, "scrollWidth", { configurable: true, value: 260 });
    bindScrollReveal(container, owner, ".candidate-title-track");

    expect(container.classList.contains("overflowing")).toBe(true);
    owner.dispatchEvent(new FocusEvent("focusin"));
    expect(track.style.transform).toBe("translateX(-200px)");
  });

  it("marks overflowing tracks, keeps the container out of the tab order, and reveals on hover", () => {
    const { container, track } = makeOverflowingReveal({ viewport: 100, track: 300 });

    expect(container.classList.contains("overflowing")).toBe(true);
    expect(container.hasAttribute("tabindex")).toBe(false);

    container.dispatchEvent(new PointerEvent("pointerenter"));

    expect(track.style.transitionDuration).toBe("800ms");
    expect(track.style.transform).toBe("translateX(-200px)");
  });

  it("scales the scroll duration with overflow, clamped to a comfortable range", () => {
    const longTrack = makeOverflowingReveal({ viewport: 100, track: 1600 });
    longTrack.container.dispatchEvent(new PointerEvent("pointerenter"));
    expect(longTrack.track.style.transitionDuration).toBe("2500ms");

    const midTrack = makeOverflowingReveal({ viewport: 100, track: 300 });
    midTrack.container.dispatchEvent(new PointerEvent("pointerenter"));
    expect(midTrack.track.style.transitionDuration).toBe("800ms");

    const shortTrack = makeOverflowingReveal({ viewport: 100, track: 105 });
    shortTrack.container.dispatchEvent(new PointerEvent("pointerenter"));
    expect(shortTrack.track.style.transitionDuration).toBe("250ms");
  });

  it("returns the track to origin when the pointer leaves", () => {
    const { container, track } = makeOverflowingReveal({ viewport: 100, track: 300 });

    container.dispatchEvent(new PointerEvent("pointerenter"));
    container.dispatchEvent(new PointerEvent("pointerleave"));

    expect(track.style.transform).toBe("translateX(0)");
    expect(track.style.transitionDuration).toBe("400ms");
  });

  it("returns the track to origin when focus leaves, mirroring hover", () => {
    const { owner, track } = makeOverflowingReveal({ viewport: 100, track: 300 });

    owner.dispatchEvent(new FocusEvent("focusin"));
    expect(track.style.transform).toBe("translateX(-200px)");

    owner.dispatchEvent(new FocusEvent("focusout"));
    expect(track.style.transform).toBe("translateX(0)");
  });

  it("clamps the return duration to a comfortable range", () => {
    const longTrack = makeOverflowingReveal({ viewport: 100, track: 1600 });
    longTrack.container.dispatchEvent(new PointerEvent("pointerenter"));
    longTrack.container.dispatchEvent(new PointerEvent("pointerleave"));
    expect(longTrack.track.style.transitionDuration).toBe("1200ms");

    const shortTrack = makeOverflowingReveal({ viewport: 100, track: 105 });
    shortTrack.container.dispatchEvent(new PointerEvent("pointerenter"));
    shortTrack.container.dispatchEvent(new PointerEvent("pointerleave"));
    expect(shortTrack.track.style.transitionDuration).toBe("150ms");
  });

  it("keeps the container in the non-overflow state when content fits", () => {
    const { container, track } = makeOverflowingReveal({ viewport: 300, track: 100 });

    expect(container.classList.contains("overflowing")).toBe(false);
    expect(container.hasAttribute("tabindex")).toBe(false);

    container.dispatchEvent(new PointerEvent("pointerenter"));
    expect(track.style.transform).toBe("");
  });

  it("respects prefers-reduced-motion by using a zero transition duration", () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = (() => ({ matches: true }) as unknown) as typeof window.matchMedia;

    try {
      const { container, track } = makeOverflowingReveal({ viewport: 100, track: 300 });
      container.dispatchEvent(new PointerEvent("pointerenter"));
      expect(track.style.transitionDuration).toBe("0ms");

      container.dispatchEvent(new PointerEvent("pointerleave"));
      expect(track.style.transitionDuration).toBe("0ms");
    } finally {
      window.matchMedia = originalMatchMedia;
    }
  });
});
