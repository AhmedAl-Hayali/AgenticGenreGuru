import { confirmTrack, readJsonMaybe, searchTracks } from "./api.ts";
import type { ApiConfig, ConfirmResponse, Match, SearchResponse } from "./dto.ts";
import { outcomeFor } from "./errors.ts";
import { Messages } from "./messages.ts";
import { renderCandidates, renderFingerprint } from "./render.ts";

/** DOM element references the controller uses; built once at bootstrap. */
export interface PageContainers {
  form: HTMLFormElement;
  query: HTMLInputElement;
  searchButton: HTMLButtonElement;
  status: HTMLElement;
  candidates: HTMLUListElement;
  resultSection: HTMLElement;
  resultTitle: HTMLElement;
  result: HTMLElement;
}

/** Drives the search → select → confirm → render flow; `actionSeq` discards stale in-flight responses. */
export class PageController {
  private readonly config: ApiConfig;
  private readonly containers: PageContainers;
  private actionSeq = 0;

  constructor(config: ApiConfig, containers: PageContainers) {
    this.config = config;
    this.containers = containers;
  }

  mount() {
    this.containers.form.addEventListener("submit", this.onSearch);
  }

  private setStatus = (message: string, isError?: boolean) => {
    const { status } = this.containers;
    status.textContent = message;
    status.classList.toggle("error", Boolean(isError));
  };

  private setBusy = (busy: boolean) => {
    const { searchButton, query } = this.containers;
    searchButton.disabled = busy;
    query.disabled = busy;
  };

  private isCurrent = (seq: number) => seq === this.actionSeq;

  /** Await `fn`, then return its value only if `seq` is still the active action; `undefined` if superseded. */
  private async guarded<T>(seq: number, fn: () => Promise<T>): Promise<T | undefined> {
    const value = await fn();
    return this.isCurrent(seq) ? value : undefined;
  }

  private markSelected = (listItem: HTMLLIElement) => {
    for (const item of this.containers.candidates.children) {
      item.classList.remove("selected");
      item.setAttribute("aria-pressed", "false");
    }
    listItem.classList.add("selected");
    listItem.setAttribute("aria-pressed", "true");
  };

  /** Two-click state machine: first click selects + shows hint; second click confirms. */
  private handleCandidateClick = (match: Match, listItem: HTMLLIElement) => {
    if (listItem.classList.contains("processing")) {
      return;
    }
    if (listItem.classList.contains("selected")) {
      this.confirmMatch(match, listItem);
      return;
    }
    this.markSelected(listItem);
    this.setStatus(Messages.selectedMatch(match.title));
  };

  /** Validate the query, fire the search, render candidates or an error; discards superseded responses. */
  private onSearch = async (event: SubmitEvent) => {
    event.preventDefault();
    const { query, resultSection, candidates } = this.containers;
    const trimmed = query.value.trim();
    if (!trimmed) {
      this.actionSeq += 1; // Deregister any in-flight action, like a real search would.
      resultSection.classList.add("hidden");
      candidates.replaceChildren();
      this.setStatus(Messages.emptyQuery, true);
      query.focus();
      return;
    }

    const seq = ++this.actionSeq;
    resultSection.classList.add("hidden");
    this.setStatus(Messages.searching);
    this.setBusy(true);
    candidates.replaceChildren();

    try {
      const response = await this.guarded(seq, () => searchTracks(this.config, trimmed));
      if (!response) {
        return;
      }

      if (!response.ok) {
        const body = await this.guarded(seq, () => readJsonMaybe(response));
        if (!body) {
          return;
        }
        switch (outcomeFor(response, body)) {
          case "notFound":
            this.setStatus(Messages.noResults, true);
            break;
          case "networkDown":
            this.setStatus(Messages.searchNetworkDown, true);
            break;
          default:
            this.setStatus(Messages.genericSearch, true);
        }
        return;
      }

      const body = await this.guarded(seq, () => readJsonMaybe<SearchResponse>(response));
      if (!body) {
        return;
      }

      if (!Array.isArray(body.matches)) {
        this.setStatus(Messages.genericSearch, true);
        return;
      }
      const matches = body.matches;
      if (matches.length === 0) {
        this.setStatus(Messages.noResults);
        return;
      }
      renderCandidates(candidates, matches, this.handleCandidateClick);
      this.setStatus(Messages.foundMatches(matches.length));
    } catch {
      if (!this.isCurrent(seq)) {
        return;
      }
      this.setStatus(Messages.searchNetworkDown, true);
    } finally {
      if (this.isCurrent(seq)) {
        this.setBusy(false);
      }
    }
  };

  /** Confirm the match via POST, then render fingerprint or error; newer actions cancel side-effects via `actionSeq`. */
  private confirmMatch = async (match: Match, listItem: HTMLLIElement) => {
    const { resultSection, resultTitle, result } = this.containers;
    const seq = ++this.actionSeq;
    listItem.classList.add("processing");
    resultSection.classList.add("hidden");
    this.setStatus(Messages.fetching(match.title));
    this.setBusy(true);

    try {
      const response = await this.guarded(seq, () => confirmTrack(this.config, match));
      if (!response) {
        return;
      }
      const body = await this.guarded(seq, () => readJsonMaybe(response));
      if (!body) {
        return;
      }

      if (response.ok) {
        renderFingerprint(
          resultSection,
          resultTitle,
          result,
          body as ConfirmResponse,
          this.config.featureLabels,
        );
        this.setStatus(Messages.fingerprintStored);
      } else {
        switch (outcomeFor(response, body)) {
          case "unprocessable":
            this.setStatus(Messages.audioUnprocessable(match.title), true);
            break;
          case "networkDown":
            this.setStatus(Messages.confirmNetworkDown, true);
            break;
          default:
            this.setStatus(Messages.genericConfirm, true);
        }
      }
    } catch (error) {
      if (!this.isCurrent(seq)) {
        return;
      }
      if (error instanceof TypeError) {
        // Fail-loud: propagate programmer errors (renderFingerprint's
        // missing-featureLabels guard) instead of misreporting them as a
        // network disconnect.
        throw error;
      }
      this.setStatus(Messages.confirmNetworkDown, true);
    } finally {
      if (this.isCurrent(seq)) {
        listItem.classList.remove("processing");
        this.setBusy(false);
      }
    }
  };
}
