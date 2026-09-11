/**
 * Horizontal offset (px) that fully reveals an overflowing inline block
 * inside a fixed-width container: positive only when the content is wider
 * than the viewport. jsdom reports zero widths, so this pure function is
 * exercised by unit tests while the browser binding measures real layout.
 */
export function computeScrollDistance(containerWidth: number, contentWidth: number) {
  return Math.max(0, contentWidth - containerWidth);
}

const SCROLL_MS_PER_PX = 4;
const SCROLL_MIN_MS = 250;
const SCROLL_MAX_MS = 2500;
const SCROLL_RETURN_MS_PER_PX = 2;
const SCROLL_RETURN_MIN_MS = 150;
const SCROLL_RETURN_MAX_MS = 1200;
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

/** Transition duration (ms) for a given scroll distance and per-pixel pace, clamped to [minMs, maxMs]. */
function scrollDuration(distance: number, perPx: number, minMs: number, maxMs: number) {
  return Math.min(maxMs, Math.max(minMs, distance * perPx));
}

/**
 * Wire the clip-and-reveal behavior of a container whose inline track can
 * overflow it.
 *
 * When the track content overflows its container, the container is marked
 * `overflowing` (shows the right-edge "…" fade). The container itself stays
 * out of the tab order: focus lands on the owning focus owner (e.g. a whole
 * candidate line), and this binding scrolls the track in and out with that
 * element's focus. On hover/focus it animates the track left to the end —
 * duration proportional to the distance, so any length of content scrolls at
 * a similar perceived pace — and holds the full extent in view; leave/blur
 * slides it back at a faster but still proportional pace, so it never snaps
 * for long tracks. Points to the referenced minimal pattern
 * (stackoverflow.com/a/34884309) with the distance measured at runtime
 * instead of hardcoded.
 */
export function bindScrollReveal(
  container: HTMLElement,
  focusOwner: HTMLElement = container,
  trackSelector = ".candidate-artists-track",
) {
  const track = container.querySelector<HTMLElement>(trackSelector);
  const reducedMotion = window.matchMedia?.(REDUCED_MOTION_QUERY);
  if (!track) {
    return;
  }

  const measure = () => {
    const distance = computeScrollDistance(container.clientWidth, track.scrollWidth);
    container.classList.toggle("overflowing", distance > 0);
    if (distance === 0) {
      track.style.transitionDuration = "";
      track.style.transform = "";
    }
    return distance;
  };

  const reveal = () => {
    const distance = measure();
    if (distance === 0) {
      return;
    }
    const base = reducedMotion?.matches
      ? 0
      : scrollDuration(distance, SCROLL_MS_PER_PX, SCROLL_MIN_MS, SCROLL_MAX_MS);
    track.style.transitionDuration = `${base}ms`;
    track.style.transform = `translateX(${-distance}px)`;
  };

  const reset = () => {
    const distance = measure();
    const base = reducedMotion?.matches
      ? 0
      : scrollDuration(
          distance,
          SCROLL_RETURN_MS_PER_PX,
          SCROLL_RETURN_MIN_MS,
          SCROLL_RETURN_MAX_MS,
        );
    track.style.transitionDuration = `${base}ms`;
    track.style.transform = "translateX(0)";
  };

  measure();
  container.addEventListener("pointerenter", reveal);
  focusOwner.addEventListener("focusin", reveal);
  container.addEventListener("pointerleave", reset);
  focusOwner.addEventListener("focusout", reset);
}
