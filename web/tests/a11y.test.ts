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

  it("switches a preview on with the Enter key on its button, without selecting or confirming", async () => {
    const els = await bootWithMatch();
    const listItem = grabCandidate(els);
    const button = listItem.querySelector<HTMLButtonElement>(".candidate-preview")!;

    button.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    button.click();

    expect(listItem.classList.contains("selected")).toBe(false);
    expect(listItem.getAttribute("aria-pressed")).toBe("false");
    expect(button.classList.contains("playing")).toBe(true);
    expect(button.getAttribute("aria-pressed")).toBe("true");
    expect(els.fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/confirm/"),
      expect.anything(),
    );
  });

  it("switches a preview off with the Space key on its button and deselects nothing", async () => {
    const els = await bootWithMatch();
    const listItem = grabCandidate(els);
    const button = listItem.querySelector<HTMLButtonElement>(".candidate-preview")!;

    button.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true }));
    button.click();
    button.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true }));
    button.click();

    expect(listItem.classList.contains("selected")).toBe(false);
    expect(button.classList.contains("playing")).toBe(false);
    expect(button.hasAttribute("aria-pressed")).toBe(false);
  });
});
