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
});

beforeEach(() => {
  installIntersectionObserver();
});
