import { describe, it, expect, vi } from "vitest";
import {
  MATCH,
  bootApp,
  grabCandidate,
  jsonResponse,
  submitSearch,
  waitForCandidate,
} from "./helpers.ts";

describe("keyboard accessibility (a11y)", () => {
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

  it("ignores non-activating keys on a candidate", async () => {
    const els = await bootWithMatch();
    const listItem = grabCandidate(els);

    listItem.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));

    expect(listItem.classList.contains("selected")).toBe(false);
    expect(listItem.getAttribute("aria-pressed")).toBe("false");
  });
});
