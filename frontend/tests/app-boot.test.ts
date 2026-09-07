import { describe, it, expect, vi } from "vitest";
import { MATCH, bootApp, jsonResponse } from "./helpers.ts";

describe("app boot + config", () => {
  it("builds confirm requests against the configured confirm URL", async () => {
    const els = await bootApp();
    els.fetchMock.mockResolvedValue(jsonResponse({ status: "success", matches: [MATCH] }));
    els.query.value = "Daft Punk";
    els.form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    await vi.waitFor(() => {
      expect(els.fetchMock).toHaveBeenCalledWith(
        "/api/search/?query=Daft%20Punk",
        expect.anything(),
      );
    });
    await vi.waitFor(() => {
      expect(document.querySelector("#candidates li")).not.toBeNull();
    });

    (document.querySelector("#candidates li") as HTMLElement).click();
    (document.querySelector("#candidates li") as HTMLElement).click();

    await vi.waitFor(() => {
      expect(els.fetchMock).toHaveBeenCalledWith("/api/confirm/", expect.anything());
    });
  });
});
