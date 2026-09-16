import { describe, expect, it, beforeEach } from "vitest";
import { applyTheme, mountThemeSwitch, resolveTheme } from "../fingerprint_app/ts/theme.ts";

/** Build the theme-toggle markup as the page header partial ships it. */
function toggleHtml(): string {
  return `
    <button type="button" id="theme-toggle" class="theme-toggle" aria-label="Switch to light theme">
      <svg class="theme-toggle-icon moon" aria-hidden="true" width="24" height="24"><path d="M12,3c-4.97,0-9,4.03-9,9s4.03,9,9,9s9-4.03,9-9c0-0.46-0.04-0.92-0.1-1.36c-0.98,1.37-2.58,2.26-4.4,2.26 c-2.98,0-5.4-2.42-5.4-5.4c0-1.81,0.89-3.42,2.26-4.4C12.92,3.04,12.46,3,12,3L12,3z"/></svg>
      <svg class="theme-toggle-icon sun" aria-hidden="true" width="24" height="24"><path d="M12,7c-2.76,0-5,2.24-5,5s2.24,5,5,5s5-2.24,5-5S14.76,7,12,7L12,7z M2,13l2,0c0.55,0,1-0.45,1-1s-0.45-1-1-1l-2,0 c-0.55,0-1,0.45-1,1S1.45,13,2,13z M20,13l2,0c0.55,0,1-0.45,1-1s-0.45-1-1-1l-2,0c-0.55,0-1,0.45-1,1S19.45,13,20,13z M11,2v2 c0,0.55,0.45,1,1,1s1-0.45,1-1V2c0-0.55-0.45-1-1-1S11,1.45,11,2z M11,20v2c0,0.55,0.45,1,1,1s1-0.45,1-1v-2c0-0.55-0.45-1-1-1 C11.45,19,11,19.45,11,20z M5.99,4.58c-0.39-0.39-1.03-0.39-1.41,0c-0.39,0.39-0.39,1.03,0,1.41l1.06,1.06 c0.39,0.39,1.03,0.39,1.41,0s0.39-1.03,0-1.41L5.99,4.58z M18.36,16.95c-0.39-0.39-1.03-0.39-1.41,0c-0.39,0.39-0.39,1.03,0,1.41 l1.06,1.06c0.39,0.39,1.03,0.39,1.41,0c0.39-0.39,0.39-1.03,0-1.41L18.36,16.95z M19.42,5.99c0.39-0.39,0.39-1.03,0-1.41 c-0.39-0.39-1.03-0.39-1.41,0l-1.06,1.06c-0.39,0.39-0.39,1.03,0,1.41s1.03,0.39,1.41,0L19.42,5.99z M7.05,18.36 c0.39-0.39,0.39-1.03,0-1.41c-0.39-0.39-1.03-0.39-1.41,0l-1.06,1.06c-0.39,0.39-0.39,1.03,0,1.41s1.03,0.39,1.41,0L7.05,18.36z"/></svg>
    </button>
  `;
}

describe("resolveTheme", () => {
  it("prefers the stored theme over the OS preference", () => {
    const storage = { getItem: () => "selenized-light" };
    expect(resolveTheme(storage, false)).toBe("selenized-light");
    expect(resolveTheme(storage, true)).toBe("selenized-light");
  });

  it("falls back to the light theme when no stored choice and the OS prefers light", () => {
    expect(resolveTheme({ getItem: () => null }, true)).toBe("selenized-light");
  });

  it("falls back to the black theme when no stored choice and the OS prefers dark", () => {
    expect(resolveTheme({ getItem: () => null }, false)).toBe("selenized-black");
  });

  it("ignores an unknown or retired stored value", () => {
    expect(resolveTheme({ getItem: () => "selenized-dark" }, true)).toBe("selenized-light");
    expect(resolveTheme({ getItem: () => "" }, false)).toBe("selenized-black");
  });

  it("ignores an unreadable storage", () => {
    const storage = {
      getItem: () => {
        throw new Error("storage blocked");
      },
    };
    expect(resolveTheme(storage, true)).toBe("selenized-light");
  });

  it("treats null storage as no stored choice", () => {
    expect(resolveTheme(null, false)).toBe("selenized-black");
  });
});

describe("applyTheme", () => {
  beforeEach(() => {
    document.documentElement.removeAttribute("data-theme");
    localStorage.clear();
  });

  it("applies the theme to the document root and persists it", () => {
    applyTheme("selenized-light", localStorage);
    expect(document.documentElement.getAttribute("data-theme")).toBe("selenized-light");
    expect(localStorage.getItem("gg-theme")).toBe("selenized-light");
  });

  it("still applies the theme when storage writes fail", () => {
    const storage = {
      setItem: () => {
        throw new Error("storage blocked");
      },
    };
    applyTheme("selenized-black", storage);
    expect(document.documentElement.getAttribute("data-theme")).toBe("selenized-black");
  });

  it("tolerates null storage", () => {
    applyTheme("selenized-black", null);
    expect(document.documentElement.getAttribute("data-theme")).toBe("selenized-black");
  });
});

describe("mountThemeSwitch", () => {
  beforeEach(() => {
    document.documentElement.removeAttribute("data-theme");
    document.body.innerHTML = "";
    localStorage.clear();
  });

  it("is a no-op when no toggle is present", () => {
    expect(() => mountThemeSwitch(document, null, false)).not.toThrow();
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });

  it("syncs the toggle and glyph to the stored theme", () => {
    document.body.innerHTML = toggleHtml();
    const storage = { getItem: () => "selenized-light", setItem: () => {} };
    mountThemeSwitch(document, storage, false);
    expect(document.documentElement.getAttribute("data-theme")).toBe("selenized-light");
    expect(document.querySelector("#theme-toggle")!.getAttribute("aria-label")).toBe(
      "Switch to dark theme",
    );
  });

  it("applies the system theme when nothing is stored", () => {
    document.body.innerHTML = toggleHtml();
    mountThemeSwitch(document, null, true);
    expect(document.documentElement.getAttribute("data-theme")).toBe("selenized-light");
  });

  it("shows the moon glyph from the default black theme", () => {
    document.body.innerHTML = toggleHtml();
    mountThemeSwitch(document, null, false);
    expect(document.documentElement.getAttribute("data-theme")).toBe("selenized-black");
    expect(document.querySelector("#theme-toggle")!.getAttribute("aria-label")).toBe(
      "Switch to light theme",
    );
  });

  it("toggles the theme and label on click and persists", () => {
    document.body.innerHTML = toggleHtml();
    mountThemeSwitch(document, localStorage, false);

    const button = document.querySelector<HTMLButtonElement>("#theme-toggle")!;
    button.click();

    expect(document.documentElement.getAttribute("data-theme")).toBe("selenized-light");
    expect(document.querySelector("#theme-toggle")!.getAttribute("aria-label")).toBe(
      "Switch to dark theme",
    );
    expect(localStorage.getItem("gg-theme")).toBe("selenized-light");

    button.click();

    expect(document.documentElement.getAttribute("data-theme")).toBe("selenized-black");
    expect(localStorage.getItem("gg-theme")).toBe("selenized-black");
  });

  it("keeps resolving a stored choice after a click", () => {
    document.body.innerHTML = toggleHtml();
    mountThemeSwitch(document, localStorage, false);
    document.querySelector<HTMLButtonElement>("#theme-toggle")!.click();

    document.body.innerHTML = "";
    document.documentElement.removeAttribute("data-theme");
    document.body.innerHTML = toggleHtml();
    mountThemeSwitch(document, localStorage, true);
    expect(document.documentElement.getAttribute("data-theme")).toBe("selenized-light");
  });
});
