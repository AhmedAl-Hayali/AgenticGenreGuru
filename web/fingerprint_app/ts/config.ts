import type { ApiConfig } from "./dto.ts";

/** Read the `#api-config` JSON blob as `ApiConfig`; throws if missing. */
export function loadConfig(root: ParentNode = document): ApiConfig {
  const configElement = root.querySelector<HTMLScriptElement>("#api-config");
  if (!configElement) {
    throw new Error("Missing #api-config JSON blob; cannot bootstrap the UI.");
  }
  return JSON.parse(configElement.textContent ?? "") as ApiConfig;
}
