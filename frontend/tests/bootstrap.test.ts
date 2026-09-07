// Bootstrap robustness: the index-page partials must all render the required
// ids and the #api-config blob must be present and parseable, otherwise the
// page fails loudly at boot instead of limping along half-wired.

import { describe, expect, it, vi } from "vitest";
import { loadConfig } from "../fingerprint_app/ts/config.ts";
import { CONFIG, fixtureHtml } from "./helpers.ts";

async function importIndexPage() {
  vi.resetModules();
  await import("../fingerprint_app/ts/pages/index-page.ts");
}

describe("bootstrap", () => {
  it("throws at boot when a required container id is missing", async () => {
    document.body.innerHTML = fixtureHtml(CONFIG);
    document.querySelector("#query")!.remove();

    await expect(importIndexPage()).rejects.toThrow(/Missing #query element/);
  });

  it("throws at boot when the #api-config blob is missing", async () => {
    document.body.innerHTML = fixtureHtml(CONFIG).replace(
      '<script id="api-config" type="application/json">',
      '<script type="application/json">',
    );

    await expect(importIndexPage()).rejects.toThrow(/Missing #api-config JSON blob/);
  });

  it("propagates a parse error for a malformed #api-config blob", async () => {
    document.body.innerHTML = fixtureHtml(CONFIG).replace(
      /(<script id="api-config" type="application\/json">).*(<\/script>)/s,
      '$1{"searchPattern": </script>',
    );

    await expect(importIndexPage()).rejects.toThrow();
  });

  it("propagates a parse error for an empty #api-config blob", async () => {
    document.body.innerHTML = fixtureHtml(CONFIG).replace(
      /(<script id="api-config" type="application\/json">).*(<\/script>)/s,
      "$1</script>",
    );

    await expect(importIndexPage()).rejects.toThrow();
  });

  it("config loader throws when its root has no #api-config", () => {
    const root = document.createElement("div");
    expect(() => loadConfig(root)).toThrow(/Missing #api-config JSON blob/);
  });
});
