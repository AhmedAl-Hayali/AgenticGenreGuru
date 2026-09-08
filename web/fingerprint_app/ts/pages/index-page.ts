import { loadConfig } from "../config.ts";
import { PageController } from "../page-controller.ts";

/** Get an element by `id` and cast to `T`; throws on missing so misconfigured partials fail loudly at boot. */
function requireById<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(
      `Missing #${id} element. Check that the fingerprint_app partials all rendered.`,
    );
  }
  return element as T;
}

const containers = {
  form: requireById<HTMLFormElement>("search-form"),
  query: requireById<HTMLInputElement>("query"),
  searchButton: requireById<HTMLButtonElement>("search-btn"),
  status: requireById<HTMLElement>("status"),
  candidates: requireById<HTMLUListElement>("candidates"),
  resultSection: requireById<HTMLElement>("result-section"),
  resultTitle: requireById<HTMLElement>("result-title"),
  result: requireById<HTMLElement>("result"),
};

const controller = new PageController(loadConfig(), containers);
controller.mount();
