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
  describe("onSearch", () => {
    it("warns on an empty query without contacting the API", async () => {
      const els = await bootApp();
      els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

      expect(els.fetchMock).not.toHaveBeenCalled();
      expect(els.status.textContent).toBe("Enter a song title to search.");
      expect(els.query.matches(":focus")).toBe(true);
    });

    it("clears previous results on an empty re-submit", async () => {
      const els = await bootApp();
      els.fetchMock.mockResolvedValue(jsonResponse({ status: "success", matches: [MATCH] }));
      submitSearch(els, "Daft Punk");
      await waitForCandidate(els);
      expect(els.candidates.children.length).toBe(1);

      els.query.value = "";
      els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

      expect(els.candidates.children.length).toBe(0);
      expect(els.status.textContent).toBe("Enter a song title to search.");
      expect(els.status.classList.contains("error")).toBe(true);
    });

    it("shows the no-results message on an empty match list", async () => {
      const els = await bootApp();
      els.fetchMock.mockResolvedValue(jsonResponse({ status: "success", matches: [] }));

      els.query.value = "zzzz";
      els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

      await vi.waitFor(() => {
        expect(els.status.textContent).toContain("No results found.");
      });
      expect(els.candidates.children.length).toBe(0);
    });

    it("treats a malformed success body as a generic search error", async () => {
      const els = await bootApp();
      els.fetchMock.mockResolvedValue(jsonResponse({ status: "success" }));

      submitSearch(els);

      await vi.waitFor(() => {
        expect(els.status.textContent).toContain("Search failed. Please try again.");
      });
      expect(els.status.classList.contains("error")).toBe(true);
    });

    const searchErrorCases: Array<{
      httpStatus: number;
      body: Record<string, unknown>;
      message: string;
    }> = [
      {
        httpStatus: 503,
        body: { status: "error", error: "NetworkDisconnectedError" },
        message: "Network disconnected.",
      },
      {
        httpStatus: 404,
        body: { status: "error", error: "TrackNotFoundError" },
        message: "No results found.",
      },
      { httpStatus: 500, body: { status: "error" }, message: "Search failed. Please try again." },
    ];

    describe.each(searchErrorCases)(
      "search error mapping (HTTP $httpStatus)",
      ({ httpStatus, body, message }) => {
        it("shows the mapped message", async () => {
          const els = await bootApp();
          els.fetchMock.mockResolvedValue(jsonResponse(body, httpStatus));

          submitSearch(els);

          await vi.waitFor(() => {
            expect(els.status.textContent).toContain(message);
          });
          expect(els.status.classList.contains("error")).toBe(true);
        });
      },
    );

    it("maps a timed-out search request to the reachability message", async () => {
      vi.useFakeTimers();
      const els = await bootApp();
      els.fetchMock.mockImplementation(abortAwareFetch());

      submitSearch(els);

      await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS);
      vi.useRealTimers();

      await vi.waitFor(() => {
        expect(els.status.textContent).toContain("Network disconnected.");
      });
    });

    it("recovers when a search request is aborted outright (AbortError)", async () => {
      const els = await bootApp();
      els.fetchMock.mockRejectedValue(new DOMException("The operation was aborted.", "AbortError"));

      submitSearch(els);

      await vi.waitFor(() => {
        expect(els.status.textContent).toContain("Network disconnected.");
        expect(els.searchButton.disabled).toBe(false);
      });
    });

    it("pluralizes the match count and shows the select hint", async () => {
      const els = await bootApp();
      els.fetchMock.mockResolvedValue(
        jsonResponse({ status: "success", matches: [MATCH, MINIMAL_MATCH] }),
      );

      submitSearch(els);
      await vi.waitFor(() => {
        expect(els.candidates.children.length).toBe(2);
      });

      expect(els.status.textContent).toContain("Found 2 matches.");
      expect(els.status.textContent).toContain("Click a match once to select");
    });
  });

  describe("selection", () => {
    it("moves selection to a newly clicked candidate", async () => {
      const els = await bootApp();
      els.fetchMock.mockResolvedValue(
        jsonResponse({ status: "success", matches: [MATCH, MINIMAL_MATCH] }),
      );

      submitSearch(els);
      await vi.waitFor(() => {
        expect(els.candidates.children.length).toBe(2);
      });

      const rows = Array.from(els.candidates.children) as HTMLElement[];
      const first = rows[0]!;
      const second = rows[1]!;

      first.click();
      expect(first.classList.contains("selected")).toBe(true);
      expect(first.getAttribute("aria-pressed")).toBe("true");

      second.click();
      expect(first.classList.contains("selected")).toBe(false);
      expect(first.getAttribute("aria-pressed")).toBe("false");
      expect(second.classList.contains("selected")).toBe(true);
      expect(second.getAttribute("aria-pressed")).toBe("true");
      expect(els.status.textContent).toContain('Selected "Around the World"');
    });
  });


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
    it("renders fingerprint feature rows on success", async () => {
      const els = await bootDoubleClickConfirm();

      await vi.waitFor(() => {
        expect(els.resultSection.classList.contains("hidden")).toBe(false);
      });
      expect(els.resultTitle.textContent).toBe("Fingerprint stored");
      expect(els.result.textContent).toContain("Song ID");
      expect(els.result.textContent).toContain("Spectral Centroid (Hz)");
      expect(els.result.textContent).toContain("2500.5000");
      expect(els.result.textContent).toContain("Vector Length");
      expect(els.status.textContent).toBe("Fingerprint stored successfully.");
    });

    const confirmErrorCases: Array<{
      confirmStatus: number;
      confirmBody: Record<string, unknown>;
      message: string;
    }> = [
      {
        confirmStatus: 400,
        confirmBody: { status: "error", error: "AudioProcessingError" },
        message: "The audio file cannot be processed",
      },
      {
        confirmStatus: 503,
        confirmBody: { status: "error", error: "NetworkDisconnectedError" },
        message: "Network disconnected.",
      },
      {
        confirmStatus: 500,
        confirmBody: { status: "error" },
        message: "Could not confirm this match. Please try again.",
      },
    ];

    describe.each(confirmErrorCases)(
      "confirm error mapping (HTTP $confirmStatus)",
      ({ confirmStatus, confirmBody, message }) => {
        it("shows the mapped message", async () => {
          const els = await bootDoubleClickConfirm(confirmStatus, confirmBody);

          await vi.waitFor(() => {
            expect(els.status.textContent).toContain(message);
          });
        });
      },
    );


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

    it("drops a stale success response that settles after a newer search", async () => {
      const els = await bootApp();
      const { search } = await setupSearchSupersede(els);

      search.resolve(jsonResponse({ status: "success", matches: [] }));
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
