/** localStorage key for persisting the user's theme preference. */
export const THEME_KEY = "gg-theme";

/** Theme type: selenized-black or selenized-light. */
export type Theme = "selenized-black" | "selenized-light";

/** Theme toggle mounted on `#theme-toggle`; glyph visibility handled by CSS `[data-theme]` rules on `.moon`/`.sun` SVG children. */
export function mountThemeSwitch(
  root: ParentNode = document,
  storage: Pick<Storage, "getItem" | "setItem"> | null = window.localStorage,
  prefersLight: boolean = typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: light)").matches,
): void {
  const button = root.querySelector<HTMLButtonElement>("#theme-toggle");
  if (!button) {
    return;
  }

  const sync = (theme: Theme): void => {
    applyTheme(theme, storage);
    const next = theme === "selenized-black" ? "selenized-light" : "selenized-black";
    button.setAttribute(
      "aria-label",
      `Switch to ${next === "selenized-light" ? "light" : "dark"} theme`,
    );
  };

  // Re-assert in case the pre-paint bundle never ran (e.g. tests, no-JS).
  let theme = resolveTheme(storage, prefersLight);
  sync(theme);

  button.addEventListener("click", () => {
    theme = theme === "selenized-black" ? "selenized-light" : "selenized-black";
    sync(theme);
  });
}

/** Apply *theme* to the document root and persist it; storage is best-effort. */
export function applyTheme(theme: Theme, storage: Pick<Storage, "setItem"> | null): void {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    storage?.setItem(THEME_KEY, theme);
  } catch {
    // Storage unavailable — the choice still holds for this session.
  }
}

/** Resolve the initial theme: an explicit stored choice wins, otherwise fall
 * back to the OS light/dark preference. This module is the tested source.
 */
export function resolveTheme(
  storage: Pick<Storage, "getItem"> | null,
  prefersLight: boolean,
): Theme {
  let stored: string | null = null;
  try {
    stored = storage?.getItem(THEME_KEY) ?? null;
  } catch {
    // Storage unavailable (private mode/disabled) — fall back to the system.
  }
  if (stored === "selenized-black" || stored === "selenized-light") return stored as Theme;
  return prefersLight ? "selenized-light" : "selenized-black";
}
