import { describe, it, expect, vi } from "vitest";
import { MATCH, bootApp, jsonResponse } from "./helpers.ts";
import { abortAwareFetch } from "./setup.ts";
import { REQUEST_TIMEOUT_MS } from "../fingerprint_app/ts/api.ts";

describe("request robustness", () => {
  it("maps a timed-out search request to the reachability message", async () => {
    vi.useFakeTimers();
    const els = await bootApp();
    els.fetchMock.mockImplementation(abortAwareFetch());

    els.query.value = "Daft Punk";
    els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS);
    vi.useRealTimers();

    await vi.waitFor(() => {
      expect(els.status.textContent).toContain("Network disconnected.");
    });
  });

  it("recovers when a request is aborted outright (AbortError)", async () => {
    const els = await bootApp();
    els.fetchMock.mockRejectedValue(new DOMException("The operation was aborted.", "AbortError"));

    els.query.value = "Daft Punk";
    els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    await vi.waitFor(() => {
      expect(els.status.textContent).toContain("Network disconnected.");
      expect(els.searchButton.disabled).toBe(false);
    });
  });

  it("ignores a stale response when a newer search supersedes it", async () => {
    const els = await bootApp();

    let resolveFirst: ((value: Response) => void) | undefined;
    const first = new Promise<Response>((resolve) => {
      resolveFirst = resolve;
    });
    els.fetchMock
      .mockResolvedValueOnce(first)
      .mockResolvedValue(jsonResponse({ status: "success", matches: [MATCH] }));

    els.query.value = "Daft Punk";
    els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    await vi.waitFor(() => {
      expect(els.candidates.children.length).toBe(1);
    });

    resolveFirst!(jsonResponse({ status: "success", matches: [] }));
    await vi.waitFor(() => {
      expect(els.fetchMock).toHaveBeenCalledTimes(2);
    });

    expect(els.candidates.children.length).toBe(1);
    expect(els.status.textContent).toContain("Found 1 match");
    expect(els.searchButton.disabled).toBe(false);
  });
});
