// jsdom/harness setup for the frontend contract tests. Loaded automatically
// by vitest `setupFiles`; the global `afterEach` restores timers, fakes, and
// module state so every spec starts from a clean slate.

import { afterEach, vi } from "vitest";

export function clearCookies() {
  for (const part of document.cookie.split(";")) {
    const name = part.split("=")[0]!.trim();
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  }
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
