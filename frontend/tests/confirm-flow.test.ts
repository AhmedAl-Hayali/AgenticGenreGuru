import { describe, it, expect, vi } from "vitest";
import type { ApiConfig, ConfirmResponse, Match } from "../fingerprint_app/ts/dto.ts";
import { renderFingerprint } from "../fingerprint_app/ts/render.ts";
import {
  CONFIRM_OK,
  MATCH,
  bootApp,
  findConfirmCall,
  grabCandidate,
  jsonResponse,
  submitSearch,
  waitForCandidate,
} from "./helpers.ts";

describe("confirm flow", () => {
  async function bootAndSelectConfirm({
    confirmBody,
    confirmStatus = 201,
    cookie,
    config,
  }: {
    confirmBody?: ConfirmResponse;
    confirmStatus?: number;
    cookie?: string | null;
    config?: ApiConfig;
  } = {}) {
    const els = await bootApp({ cookie, config });
    els.fetchMock.mockImplementation(async (url) => {
      if (String(url).includes("/api/search/")) {
        return jsonResponse({ status: "success", matches: [MATCH] });
      }
      if (String(url).includes("/api/confirm/")) {
        return jsonResponse(confirmBody, confirmStatus);
      }
      return jsonResponse({ status: "error" }, 404);
    });

    submitSearch(els);
    await waitForCandidate(els);

    const listItem = grabCandidate(els);
    listItem.click();
    listItem.click();
    // Confirm completes when the fetch settles: "processing" is added
    // synchronously on the second click and removed in the finally block.
    await vi.waitFor(() => {
      expect(listItem.classList.contains("processing")).toBe(false);
    });
    return els;
  }

  it("POSTs the match to the confirm URL with the CSRF token and match payload", async () => {
    const els = await bootAndSelectConfirm({ confirmBody: CONFIRM_OK });

    await vi.waitFor(() => {
      expect(els.fetchMock).toHaveBeenCalledWith("/api/confirm/", expect.anything());
    });

    const confirmCall = findConfirmCall(els.fetchMock);
    expect(confirmCall).toBeDefined();
    const [url, options] = confirmCall!;

    expect(url).toBe("/api/confirm/");
    expect(options.method).toBe("POST");
    expect((options.headers as Record<string, unknown>)["Content-Type"]).toBe("application/json");
    expect((options.headers as Record<string, unknown>)["X-CSRFToken"]).toBe("token123");

    const payload = JSON.parse(String(options.body)) as Match;
    expect(payload.deezer_id).toBe(MATCH.deezer_id);
    expect(payload.title).toBe(MATCH.title);
    expect(payload.isrc).toBe(MATCH.isrc);
    expect(payload.duration).toBe(MATCH.duration);
    expect(payload.preview).toBe(MATCH.preview);
    expect(payload.artist).toEqual(MATCH.artist);
    expect(payload.album).toEqual(MATCH.album);
  });

  it("sends an empty CSRF token when no cookie is present", async () => {
    const els = await bootAndSelectConfirm({
      confirmBody: CONFIRM_OK,
      cookie: null,
    });

    await vi.waitFor(() => {
      expect(els.fetchMock).toHaveBeenCalledWith("/api/confirm/", expect.anything());
    });
    const confirmCall = findConfirmCall(els.fetchMock);
    expect(confirmCall).toBeDefined();
    const [, options] = confirmCall!;
    expect((options.headers as Record<string, unknown>)["X-CSRFToken"]).toBe("");
  });

  it("renders fingerprint feature rows on success", async () => {
    const els = await bootAndSelectConfirm({
      confirmBody: CONFIRM_OK,
    });

    expect(els.resultSection.classList.contains("hidden")).toBe(false);
    expect(els.resultTitle.textContent).toBe("Fingerprint stored");
    expect(els.result.textContent).toContain("Song ID");
    expect(els.result.textContent).toContain("Spectral Centroid (Hz)");
    expect(els.result.textContent).toContain("2500.5000");
    expect(els.result.textContent).toContain("Vector Length");
    await vi.waitFor(() => {
      expect(els.status.textContent).toBe("Fingerprint stored successfully.");
    });
  });

  it("fails loudly when featureLabels are missing instead of rendering empty rows", () => {
    const section = document.createElement("section");
    section.classList.add("hidden");
    const title = document.createElement("p");
    const result = document.createElement("dl");

    expect(() => renderFingerprint(section, title, result, CONFIRM_OK, undefined)).toThrow(
      "featureLabels is required to render a fingerprint.",
    );
    expect(section.classList.contains("hidden")).toBe(true);
    expect(result.textContent).toBe("");
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
        const els = await bootAndSelectConfirm({ confirmStatus, confirmBody });

        await vi.waitFor(() => {
          expect(els.status.textContent).toContain(message);
        });
      });
    },
  );
});
