const LAZY_COVER_ROOT_MARGIN = "200px";

/**
 * Lazy-load candidate covers: each `.candidate-cover` with a pending
 * `data-src` starts with `src` unset (zero bytes fetched until it nears the
 * viewport). On intersect it swaps in the real URL, hides the image on load
 * error, and stops observing that row.
 */
export function bindLazyCovers(listElement: HTMLUListElement) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) {
          continue;
        }
        const listItem = entry.target as HTMLLIElement;
        const cover = listItem.querySelector<HTMLImageElement>(".candidate-cover");
        if (cover?.dataset.src) {
          cover.src = cover.dataset.src;
          cover.onerror = () => cover.classList.add("hidden");
          delete cover.dataset.src;
        }
        observer.unobserve(listItem);
      }
    },
    { rootMargin: LAZY_COVER_ROOT_MARGIN },
  );

  for (const listItem of listElement.querySelectorAll<HTMLLIElement>(".candidate")) {
    if (listItem.querySelector<HTMLImageElement>(".candidate-cover")?.dataset.src) {
      observer.observe(listItem);
    }
  }
}
