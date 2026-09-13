// jsdom/harness setup for the frontend contract tests. Loaded automatically
// by vitest `setupFiles`; the global `afterEach` restores timers, fakes, and
// module state so every spec starts from a clean slate.

import { afterEach, beforeEach, vi } from "vitest";

export function clearCookies() {
  for (const part of document.cookie.split(";")) {
    const name = part.split("=")[0]!.trim();
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  }
}

/** Handle into one stub IntersectionObserver instance. */
export interface MockObserverHandle {
  observed: Element[];
  unobserved: Element[];
  /** Fire the observer callback with synthetic entries for `target`s. */
  trigger(entries: Array<{ target: Element; isIntersecting: boolean }>): void;
}

/**
 * Stub the jsdom-missing IntersectionObserver with a controllable fake, so
 * lazy cover loading can be observed and driven by hand. Returns one handle
 * per created instance, in construction order.
 */
export function installIntersectionObserver(): MockObserverHandle[] {
  const handles: MockObserverHandle[] = [];

  class MockObserver implements IntersectionObserver {
    root: Element | Document | null = null;
    rootMargin = "0px";
    thresholds: ReadonlyArray<number> = [0];
    readonly observed: Element[] = [];
    readonly unobserved: Element[] = [];

    constructor(public callback: IntersectionObserverCallback) {
      handles.push({
        observed: this.observed,
        unobserved: this.unobserved,
        trigger: (entries) => {
          this.callback(
            entries.map(({ target, isIntersecting }) => ({
              target,
              isIntersecting,
              intersectionRatio: isIntersecting ? 1 : 0,
              boundingClientRect: new DOMRect(),
              intersectionRect: new DOMRect(),
              rootBounds: null,
              time: 0,
            })),
            this as unknown as IntersectionObserver,
          );
        },
      });
    }

    observe(target: Element) {
      this.observed.push(target);
    }

    unobserve(target: Element) {
      this.unobserved.push(target);
    }

    disconnect() {}

    takeRecords() {
      return [];
    }
  }

  vi.stubGlobal("IntersectionObserver", MockObserver);
  return handles;
}

/** Handle into one stub requestAnimationFrame/cancelAnimationFrame pair. */
export interface AnimationFrameHandle {
  /** Run all currently scheduled frame callbacks; re-scheduled ones wait for the next tick. */
  tick(): void;
  cancel: ReturnType<typeof vi.fn>;
}

/**
 * Stub requestAnimationFrame/cancelAnimationFrame with a deterministic fake so
 * the player's per-frame progress loop can be driven and torn down by hand.
 * `tick` flushes scheduled callbacks and honors cancels (a cancelled id never
 * runs); unlike jsdom's rAF, it does not wait for a pretend clock.
 */
export function installAnimationFrame(): AnimationFrameHandle {
  type Scheduled = { id: number; cb: FrameRequestCallback };
  let scheduled: Scheduled[] = [];
  let nextId = 1;
  const cancel = vi.fn((id: number) => {
    scheduled = scheduled.filter((entry) => entry.id !== id);
  });
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
    scheduled.push({ id: nextId, cb });
    return nextId++;
  });
  vi.stubGlobal("cancelAnimationFrame", cancel);
  return {
    tick: () => {
      const pending = scheduled;
      scheduled = [];
      for (const { cb } of pending) {
        cb(0);
      }
    },
    cancel,
  };
}

export function abortAwareFetch(): (
  url: RequestInfo | URL,
  options: RequestInit,
) => Promise<Response> {
  return (_url, options) =>
    new Promise<Response>((_resolve, reject) => {
      options.signal?.addEventListener("abort", () =>
        reject(new DOMException("The operation was aborted.", "AbortError")),
      );
    });
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.resetModules();
  vi.restoreAllMocks();
});

beforeEach(() => {
  installIntersectionObserver();
  // jsdom's HTMLMediaElement.play/pause are unimplemented; stub them (like the
  // IntersectionObserver above) so boot-flow tests can start and stop previews.
  vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(function (
    this: HTMLMediaElement,
  ) {
    // `paused` is readonly on the prototype; shadow it so the player's
    // same-row stop check sees a consistent state.
    Object.defineProperty(this, "paused", { value: false, configurable: true });
    return Promise.resolve();
  });
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(function (
    this: HTMLMediaElement,
  ) {
    Object.defineProperty(this, "paused", { value: true, configurable: true });
  });
});
