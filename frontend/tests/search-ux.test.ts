import { describe, it, expect, vi } from "vitest";
import {
  MATCH,
  bootApp,
  grabCandidate,
  jsonResponse,
  submitSearch,
  waitForCandidate,
} from "./helpers.ts";

describe("search UX", () => {
  it("renders one candidate row per match with a Selected badge", async () => {
    const els = await bootApp();
    els.fetchMock.mockResolvedValue(jsonResponse({ status: "success", matches: [MATCH] }));

    submitSearch(els);
    await waitForCandidate(els);

    const { status } = els;
    const listItem = grabCandidate(els);
    expect(listItem.textContent).toContain("Harder, Better, Faster, Stronger");
    expect(listItem.textContent).toContain("Daft Punk");
    expect(listItem.textContent).toContain("Discovery");
    expect(listItem.textContent).toContain("Selected");
    expect(listItem.classList.contains("selected")).toBe(false);
    expect(listItem.getAttribute("aria-pressed")).toBe("false");
    expect(status.textContent).toContain("Click a match once to select");
  });

  it("warns on an empty query without contacting the API", async () => {
    const els = await bootApp();
    els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    expect(els.fetchMock).not.toHaveBeenCalled();
    expect(els.status.textContent).toBe("Enter a song title to search.");
    expect(els.query.matches(":focus")).toBe(true);
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
});
