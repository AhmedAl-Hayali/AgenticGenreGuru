// Unit tests for the lazy cover loader (fingerprint_app/ts/lazy-image.ts).
// Builds candidate rows against the documented DOM contract (`.candidate` with a
// `.candidate-cover` whose pending URL lives in `data-src`) and drives the
// observer stub from setup.ts by hand.

import { describe, expect, it } from "vitest";
import { bindLazyCovers } from "../fingerprint_app/ts/lazy-image.ts";
import { installIntersectionObserver } from "./setup.ts";

const COVER_URL = "https://example.test/cover.jpg";

/** A candidate list whose single row has a cover waiting in `data-src`. */
function coverList(): HTMLUListElement {
  const list = document.createElement("ul");
  const item = document.createElement("li");
  item.className = "candidate";
  const cover = document.createElement("img");
  cover.className = "candidate-cover";
  cover.setAttribute("alt", "Around the World");
  cover.dataset.src = COVER_URL;
  item.appendChild(cover);
  list.appendChild(item);
  return list;
}

describe("bindLazyCovers", () => {
  it("loads the cover src when the item intersects and then unobserves it", () => {
    const handles = installIntersectionObserver();
    const list = coverList();
    bindLazyCovers(list);

    const observer = handles[0]!;
    const item = list.children[0]!;
    const cover = item.querySelector<HTMLImageElement>(".candidate-cover")!;

    expect(observer.observed).toEqual([item]);

    observer.trigger([{ target: item, isIntersecting: true }]);
    expect(cover.getAttribute("src")).toBe(COVER_URL);
    expect(cover.hasAttribute("data-src")).toBe(false);
    expect(observer.unobserved).toEqual([item]);
  });

  it("keeps the cover src deferred for items outside the viewport", () => {
    const handles = installIntersectionObserver();
    const list = coverList();
    bindLazyCovers(list);

    const observer = handles[0]!;
    const item = list.children[0]!;

    observer.trigger([{ target: item, isIntersecting: false }]);
    expect(item.querySelector<HTMLImageElement>(".candidate-cover")?.hasAttribute("src")).toBe(
      false,
    );
  });

  it("never observes covers without a pending data-src", () => {
    const handles = installIntersectionObserver();
    const list = coverList();
    list.querySelector<HTMLImageElement>(".candidate-cover")!.removeAttribute("data-src");
    bindLazyCovers(list);

    expect(handles[0]!.observed).toEqual([]);
  });

  it("hides an image that fails to load after being revealed", () => {
    const handles = installIntersectionObserver();
    const list = coverList();
    bindLazyCovers(list);

    const observer = handles[0]!;
    const item = list.children[0]!;
    const cover = item.querySelector<HTMLImageElement>(".candidate-cover")!;

    observer.trigger([{ target: item, isIntersecting: true }]);
    cover.dispatchEvent(new Event("error"));
    expect(cover.classList.contains("hidden")).toBe(true);
  });
});
