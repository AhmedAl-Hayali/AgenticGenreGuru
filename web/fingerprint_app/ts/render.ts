import type { ConfirmResponse, Match } from "./dto.ts";
import { bindScrollReveal } from "./scroll-reveal.ts";
import { Messages } from "./messages.ts";

/** Callback signature invoked when a candidate list item is clicked or activated via keyboard. */
export type CandidateClickHandler = (match: Match, listItem: HTMLLIElement) => void;

function createCandidateCover(match: Match): HTMLImageElement {
  const cover = document.createElement("img");
  cover.className = "candidate-cover";
  cover.alt = match.title;
  if (match.cover) {
    cover.src = match.cover;
    cover.onerror = () => cover.classList.add("hidden");
  } else {
    cover.classList.add("hidden");
  }
  return cover;
}

function createCandidateArtists(match: Match): HTMLElement {
  const names = match.artists.length > 0 ? match.artists.map((artist) => artist.name) : [];

  const artists = document.createElement("div");
  artists.className = "candidate-artists";
  const artistsTrack = document.createElement("span");
  artistsTrack.className = "candidate-artists-track";

  if (names.length) {
    for (const name of names) {
      const artist = document.createElement("span");
      artist.className = "candidate-artist";
      artist.textContent = name;
      artistsTrack.appendChild(artist);
    }
  } else {
    const artist = document.createElement("span");
    artist.className = "candidate-artist";
    artist.textContent = Messages.unknownArtist;
    artistsTrack.appendChild(artist);
  }

  artists.title = names.length ? names.join(", ") : Messages.unknownArtist;

  const fade = document.createElement("span");
  fade.className = "candidate-artists-fade";
  fade.setAttribute("aria-hidden", "true");
  fade.textContent = "…";

  artists.appendChild(artistsTrack);
  artists.appendChild(fade);
  return artists;
}

function createCandidateBody(match: Match): HTMLElement {
  const body = document.createElement("div");
  body.className = "candidate-body";

  const title = document.createElement("span");
  title.className = "candidate-title";
  title.textContent = match.title;
  body.appendChild(title);

  if (match.album?.title) {
    const meta = document.createElement("span");
    meta.className = "candidate-meta";
    meta.textContent = `(${match.album.title})`;
    body.appendChild(meta);
  }

  body.appendChild(createCandidateArtists(match));
  return body;
}

/** Build the candidate list in `listElement`; each `<li>` wires click/keyboard to `onCandidateClick`. */
export function renderCandidates(
  listElement: HTMLUListElement,
  matches: Match[],
  onCandidateClick: CandidateClickHandler,
) {
  listElement.replaceChildren();
  for (const match of matches) {
    const listItem = document.createElement("li");
    listItem.className = "candidate";
    listItem.tabIndex = 0;
    listItem.setAttribute("role", "button");
    listItem.setAttribute("aria-pressed", "false");

    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = Messages.badgeSelected;

    listItem.appendChild(createCandidateCover(match));
    listItem.appendChild(createCandidateBody(match));
    listItem.appendChild(badge);

    const activate = () => onCandidateClick(match, listItem);
    listItem.addEventListener("click", activate);
    listItem.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
    bindScrollReveal(
      listItem.querySelector<HTMLElement>(".candidate-artists")!,
      listItem,
      ".candidate-artists-track",
    );

    listElement.appendChild(listItem);
  }
}

/** Populate the result `<dl>` from `body`; throws `TypeError` if `featureLabels` is undefined. */
export function renderFingerprint(
  resultSection: HTMLElement,
  resultTitleElement: HTMLElement,
  resultElement: HTMLElement,
  body: ConfirmResponse,
  featureLabels?: Record<string, string>,
) {
  if (!featureLabels) {
    throw new TypeError("featureLabels is required to render a fingerprint.");
  }
  resultSection.classList.remove("hidden");
  resultTitleElement.textContent = body.title || Messages.fingerprintDefaultTitle;
  resultElement.replaceChildren();

  const fingerprint = body.fingerprint || {};

  addResultRow(resultElement, Messages.rows.songId, body.song_id);
  addResultRow(resultElement, Messages.rows.deezerId, body.deezer_id);
  addResultRow(resultElement, Messages.rows.isrc, body.isrc);
  for (const key of Object.keys(featureLabels)) {
    if (key in fingerprint) {
      addResultRow(resultElement, featureLabels[key] ?? key, formatNumber(fingerprint[key]));
    }
  }
  addResultRow(resultElement, Messages.rows.vectorLength, fingerprint.vector_length);
}

function addResultRow(resultElement: HTMLElement, term: string, definition: unknown) {
  const termElement = document.createElement("dt");
  termElement.textContent = term;
  const definitionElement = document.createElement("dd");
  definitionElement.textContent =
    definition === undefined || definition === null ? "—" : String(definition);
  resultElement.appendChild(termElement);
  resultElement.appendChild(definitionElement);
}

function formatNumber(value: unknown) {
  if (typeof value !== "number") {
    return value;
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(4);
}
