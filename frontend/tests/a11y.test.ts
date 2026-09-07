import { describe, it, expect, vi } from "vitest";
import {
  MATCH,
  bootApp,
  grabCandidate,
  jsonResponse,
  submitSearch,
  waitForCandidate,
} from "./helpers.ts";

describe("keyboard + click selection (a11y)", () => {
  async function bootWithMatch() {
    const els = await bootApp();
    els.fetchMock.mockResolvedValue(jsonResponse({ status: "success", matches: [MATCH] }));
    submitSearch(els);
    await waitForCandidate(els);
    return els;
  }

  it("selects a candidate with the Enter key", async () => {
    const els = await bootWithMatch();
    const listItem = grabCandidate(els);

    listItem.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

    expect(listItem.classList.contains("selected")).toBe(true);
    expect(listItem.getAttribute("aria-pressed")).toBe("true");
  });

  it("selects a candidate with the Space key without scrolling", async () => {
    const els = await bootWithMatch();
    const listItem = grabCandidate(els);
    const event = new KeyboardEvent("keydown", {
      key: " ",
      bubbles: true,
      cancelable: true,
    });
    const preventDefault = vi.spyOn(event, "preventDefault");
    listItem.dispatchEvent(event);

    expect(listItem.classList.contains("selected")).toBe(true);
    expect(preventDefault).toHaveBeenCalled();
  });

  it("click-to-select then click-again confirms only the selected match", async () => {
    const els = await bootWithMatch();
    const listItem = grabCandidate(els);
    els.fetchMock.mockResolvedValue(
      jsonResponse({
        status: "success",
        song_id: "11111111-1111-1111-1111-111111111111",
        deezer_id: MATCH.deezer_id,
        isrc: MATCH.isrc,
        fingerprint: { spectral_centroid: 2500.5, vector_length: 13 },
      }),
    );

    listItem.click();
    expect(els.status.textContent).toContain("Selected");
    listItem.click();

    await vi.waitFor(() => {
      expect(els.status.textContent).toBe("Fingerprint stored successfully.");
    });
  });
});
