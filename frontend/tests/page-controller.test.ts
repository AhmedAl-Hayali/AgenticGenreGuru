// Domain-spec tests for the PageController's concurrency guards and failure
// modes. Everything drives the public surface (submit events + candidate
// clicks) through `bootApp`; the private methods are exercised only via user
// actions, so these stay true contract tests.

import { describe, expect, it, vi } from "vitest";
import type { Match } from "../fingerprint_app/ts/dto.ts";
import {
  CONFIRM_OK,
  MATCH,
  BootEls,
  bootApp,
  deferred,
  expectFreshSearchState,
  grabCandidate,
  jsonResponse,
  submitSearch,
  waitForCandidate,
  withDeferredJson,
  withUnhandledRejection,
} from "./helpers.ts";

const OTHER_MATCH: Match = {
  deezer_id: 999,
  title: "Around the World",
  isrc: "GBDUW0000123",
  duration: 217,
  preview: "https://example.test/preview-other.mp3",
  artist: { id: 27, name: "Daft Punk" },
  album: { id: 302127, title: "Homework" },
};

function searchResponse(matches: Match[]) {
  return jsonResponse({ status: "success", matches });
}

async function bootWithCandidate(els: BootEls) {
  submitSearch(els, "Daft Punk");
  await waitForCandidate(els);
  return grabCandidate(els);
}

/** Drain all microtasks plus one macrotask so the controller reaches its next await site. */
async function settleTicks() {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

/** Default router: searches succeed with [MATCH], everything else is a 500. */
function routeSearchOk(url: RequestInfo | URL): Promise<Response> {
  return String(url).includes("/api/search/")
    ? Promise.resolve(searchResponse([MATCH]))
    : Promise.resolve(jsonResponse({ status: "error" }, 500));
}

/** Like `routeSearchOk`, but confirm calls reject with `reason`. */
function routeSearchOkConfirmRejects(reason: unknown) {
  return (url: RequestInfo | URL): Promise<Response> =>
    String(url).includes("/api/search/")
      ? Promise.resolve(searchResponse([MATCH]))
      : Promise.reject(reason);
}

/** Select + double-click a candidate and wait until confirmation starts. */
async function startConfirm(els: BootEls): Promise<HTMLElement> {
  const item = await bootWithCandidate(els);
  item.click();
  item.click();
  await vi.waitFor(() => {
    expect(item.classList.contains("processing")).toBe(true);
  });
  return item;
}

/** Wait until the candidate leaves its processing state (confirm settled). */
async function expectNoProcessing(item: HTMLElement) {
  await vi.waitFor(() => {
    expect(item.classList.contains("processing")).toBe(false);
  });
}

/**
 * Start a confirm via double-click, then supersede it with a newer search and
 * wait until all three fetch calls (search, confirm, newer search) have fired.
 * Returns the deferred that gates the confirm's settlement so the test can
 * resolve or reject it after the supersede.
 */
async function setupConfirmSupersede(els: BootEls) {
  const confirm = deferred<Response>();
  els.fetchMock
    .mockImplementationOnce(routeSearchOk)
    .mockImplementationOnce(() => confirm.promise)
    .mockImplementation(routeSearchOk);
  await startConfirm(els);
  submitSearch(els, "newer search");
  await vi.waitFor(() => {
    expect(els.fetchMock).toHaveBeenCalledTimes(3);
  });
  return { confirm };
}

/**
 * Run a search whose response settles immediately but whose body stays
 * pending, then supersede with a second search and wait for its candidate.
 * The body deferred is returned so the test can settle the stale body after
 * the supersede and assert it is dropped. `bodyResponse` is the `Response`
 * whose `json()` the stale body overrides.
 */
async function setupDeferredBodySupersede(els: BootEls, bodyResponse: Response) {
  const response = deferred<Response>();
  const body = deferred<unknown>();
  const wrappedResponse = withDeferredJson(bodyResponse, body.promise);
  els.fetchMock.mockImplementationOnce(() => response.promise).mockImplementation(routeSearchOk);
  submitSearch(els, "first");
  response.resolve(wrappedResponse);
  await settleTicks();
  submitSearch(els, "second");
  await waitForCandidate(els);
  return { body };
}

/**
 * Fire a deferred first search, then supersede with a second that resolves and
 * wait for its candidate. Returns the deferred gating the first search so the
 * test can settle (reject) it after the supersede.
 */
async function setupSearchSupersede(els: BootEls) {
  const search = deferred<Response>();
  els.fetchMock.mockImplementationOnce(() => search.promise).mockImplementation(routeSearchOk);
  submitSearch(els, "first");
  await settleTicks();
  submitSearch(els, "second");
  await waitForCandidate(els);
  return { search };
}

describe("page controller", () => {
  it("ignores a click on a candidate that is already processing", async () => {
    const confirm = deferred<Response>();
    const els = await bootApp();
    els.fetchMock.mockImplementationOnce(routeSearchOk).mockImplementation(() => confirm.promise);

    const item = await startConfirm(els);
    item.click();

    const confirmCalls = els.fetchMock.mock.calls.filter(([url]) =>
      String(url).includes("/api/confirm/"),
    );
    expect(confirmCalls.length).toBe(1);

    confirm.resolve(jsonResponse(CONFIRM_OK, 201));
    await expectNoProcessing(item);
  });

  it("drops an error body that settles after a newer search supersedes", async () => {
    const els = await bootApp();
    const { body } = await setupDeferredBodySupersede(els, jsonResponse({ status: "error" }, 500));

    body.resolve({});
    await vi.waitFor(() => {
      expect(els.fetchMock).toHaveBeenCalledTimes(2);
    });

    expectFreshSearchState(els);
  });

  it("drops a success body that settles after a newer search supersedes", async () => {
    const els = await bootApp();
    const { body } = await setupDeferredBodySupersede(els, searchResponse([OTHER_MATCH]));

    body.resolve({ status: "success", matches: [OTHER_MATCH] });
    await vi.waitFor(() => {
      expect(els.fetchMock).toHaveBeenCalledTimes(2);
    });

    expect(els.candidates.textContent).toContain(MATCH.title);
    expect(els.candidates.textContent).not.toContain(OTHER_MATCH.title);
    expect(els.status.textContent).toContain("Found 1 match");
  });

  it("drops a confirm response that settles after a newer search supersedes", async () => {
    const els = await bootApp();
    const { confirm } = await setupConfirmSupersede(els);

    confirm.resolve(jsonResponse(CONFIRM_OK, 201));
    await waitForCandidate(els);

    expectFreshSearchState(els, { checkHidden: true });
  });

  it("drops a confirm body that settles after a newer search supersedes", async () => {
    const els = await bootApp();
    const response = deferred<Response>();
    const body = deferred<unknown>();
    const confirmResponse = withDeferredJson(jsonResponse(CONFIRM_OK, 201), body.promise);
    els.fetchMock
      .mockImplementationOnce(routeSearchOk)
      .mockImplementationOnce(() => response.promise)
      .mockImplementation(routeSearchOk);

    await startConfirm(els);

    response.resolve(confirmResponse);
    await settleTicks();

    submitSearch(els, "newer search");
    await vi.waitFor(() => {
      expect(els.fetchMock).toHaveBeenCalledTimes(3);
    });

    body.resolve(CONFIRM_OK);
    await waitForCandidate(els);

    expect(els.resultSection.classList.contains("hidden")).toBe(true);
    expect(els.result.textContent).toBe("");
    expectFreshSearchState(els);
  });

  it("rethrows TypeError rejections instead of mapping them to a network down", async () => {
    const els = await bootApp();
    els.fetchMock.mockImplementation(routeSearchOkConfirmRejects(new TypeError("boom")));

    await withUnhandledRejection(async (reasons) => {
      const item = await startConfirm(els);
      await vi.waitFor(() => {
        expect(reasons.length).toBeGreaterThan(0);
      });
      expect(reasons[0]).toBeInstanceOf(TypeError);
      await expectNoProcessing(item);
    });
    expect(els.status.textContent).not.toContain("Network disconnected.");
    expect(els.searchButton.disabled).toBe(false);
  });

  it("maps a non-TypeError confirm rejection to the network-down message", async () => {
    const els = await bootApp();
    els.fetchMock.mockImplementation(routeSearchOkConfirmRejects(new Error("boom")));

    const item = await startConfirm(els);

    await vi.waitFor(() => {
      expect(els.status.textContent).toContain("Network disconnected.");
    });
    await expectNoProcessing(item);
    expect(els.searchButton.disabled).toBe(false);
  });

  it("drops a rejected search that settles after a newer search supersedes", async () => {
    const els = await bootApp();
    const { search } = await setupSearchSupersede(els);

    search.reject(new Error("boom"));
    await vi.waitFor(() => {
      expect(els.fetchMock).toHaveBeenCalledTimes(2);
    });

    expectFreshSearchState(els);
  });

  it("drops a rejected confirm that settles after a newer search supersedes", async () => {
    const els = await bootApp();
    const { confirm } = await setupConfirmSupersede(els);

    confirm.reject(new Error("boom"));
    await vi.waitFor(() => {
      expect(els.status.textContent).toContain("Found 1 match");
    });

    expectFreshSearchState(els, { checkHidden: true });
  });
});
