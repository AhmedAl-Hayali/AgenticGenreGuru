import type { ConfirmResponse, Match } from "./dto.ts";
import { Messages } from "./messages.ts";

/** Callback signature invoked when a candidate list item is clicked or activated via keyboard. */
export type CandidateClickHandler = (match: Match, listItem: HTMLLIElement) => void;

function candidateLabel(match: Match) {
  const artist = match.artist ? match.artist.name : Messages.unknownArtist;
  return `${match.title} · ${artist}`;
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
    listItem.tabIndex = 0;
    listItem.setAttribute("role", "button");
    listItem.setAttribute("aria-pressed", "false");

    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = Messages.badgeSelected;

    const title = document.createElement("span");
    title.className = "title";
    title.textContent = candidateLabel(match);
    if (match.album && match.album.title) {
      const meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = `(${match.album.title})`;
      title.appendChild(meta);
    }

    listItem.appendChild(badge);
    listItem.appendChild(title);
    listItem.addEventListener("click", function () {
      onCandidateClick(match, listItem);
    });
    listItem.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onCandidateClick(match, listItem);
      }
    });
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
