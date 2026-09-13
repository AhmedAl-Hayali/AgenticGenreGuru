import type { Match } from "./dto.ts";
import { Messages } from "./messages.ts";
import type { PreviewControl } from "./render.ts";

/** Played fraction as a clamped percentage; 0 when the duration is unknown. */
export function previewProgress(current: number, duration: number): number {
  if (!Number.isFinite(current) || !Number.isFinite(duration) || duration <= 0) {
    return 0;
  }
  const ratio = current / duration;
  return Math.min(1, Math.max(0, ratio)) * 100;
}

/** Options for the shared preview player. */
export interface PreviewPlayerOptions {
  /** Factory for the single shared medium; injectable so tests pass a fake. */
  createAudio?: () => HTMLAudioElement;
  /** Called when the preview fails to load or start playing. */
  onError?: (message: string) => void;
}

/**
 * Plays one 30-second song preview at a time through a single shared
 * `<audio>` element. The element is created lazily on the first interaction
 * (zero bytes fetched until a user clicks a play button) and demands
 * playback only from user gestures, so it never trips autoplay policy. The
 * active row's button carries the playing state (`playing` class +
 * `aria-pressed`) and its progress bar fills as the preview plays; stopping,
 * switching rows, or a natural end restores both.
 */
export class PreviewPlayer {
  private readonly createAudio: () => HTMLAudioElement;
  private readonly onError: (message: string) => void;
  private audio: HTMLAudioElement | null = null;
  private button: HTMLButtonElement | null = null;
  private gauge: HTMLElement | null = null;
  private rafId: number | null = null;
  private standbyLabel = "";

  constructor(options: PreviewPlayerOptions = {}) {
    this.createAudio = options.createAudio ?? (() => document.createElement("audio"));
    this.onError = options.onError ?? (() => {});
  }

  /** Toggle playback for `match` via `control`: stop if it is the active row, else play it. */
  toggle(match: Match, control: PreviewControl) {
    const { button, gauge } = control;
    if (!match.preview) {
      return;
    }
    const audio = this.ensureAudio();
    if (this.button === button && !audio.paused) {
      this.stop();
      return;
    }
    if (this.button) {
      this.resetCurrent();
    }
    this.standbyLabel = button.getAttribute("aria-label") ?? "";
    button.classList.add("playing");
    button.setAttribute("aria-pressed", "true");
    button.setAttribute("aria-label", Messages.previewStopLabel(match.title));
    this.button = button;
    this.gauge = gauge;
    this.startProgressRaf();
    audio.src = match.preview;
    this.play(audio, button);
  }

  /** Pause playback and clear the active button regardless of which row it belongs to. */
  stop() {
    this.audio?.pause();
    this.resetCurrent();
  }

  private ensureAudio(): HTMLAudioElement {
    if (this.audio) {
      return this.audio;
    }
    const audio = this.createAudio();
    audio.preload = "none";
    audio.addEventListener("ended", () => this.resetCurrent());
    audio.addEventListener("error", () => {
      if (this.button) {
        this.handleAudioError();
      }
    });
    this.audio = audio;
    return audio;
  }

  /**
   * Start playback. `play()` may reject (resource failure) or throw
   * synchronously (e.g. jsdom's stub); both are routed to the error path.
   */
  private play(audio: HTMLAudioElement, button: HTMLButtonElement) {
    try {
      void Promise.resolve(audio.play()).catch(() => {
        if (this.button === button) {
          this.handleAudioError();
        }
      });
    } catch {
      this.handleAudioError();
    }
  }

  /** Sample the media clock once per animation frame so the bar moves smoothly. */
  private readonly tickAnimationFrame = () => {
    this.updateProgress();
    if (this.button) {
      this.rafId = requestAnimationFrame(this.tickAnimationFrame);
    }
  };

  /** Arm the per-frame progress loop; only valid while a preview is active. */
  private startProgressRaf() {
    this.rafId = requestAnimationFrame(this.tickAnimationFrame);
  }

  private stopProgressRaf() {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  /** Reflect the active preview's played fraction on its progress bar. */
  private updateProgress() {
    const audio = this.audio!;
    const gauge = this.gauge!;
    const percent = previewProgress(audio.currentTime, audio.duration);
    gauge.style.setProperty("--preview-progress", `${percent}%`);
    const rounded = String(Math.round(percent));
    if (gauge.getAttribute("aria-valuenow") !== rounded) {
      gauge.setAttribute("aria-valuenow", rounded);
    }
  }

  private resetCurrent() {
    if (!this.button) {
      return;
    }
    this.stopProgressRaf();
    this.button.classList.remove("playing");
    this.button.removeAttribute("aria-pressed");
    this.button.setAttribute("aria-label", this.standbyLabel);
    this.button = null;
    if (this.gauge) {
      this.gauge.style.setProperty("--preview-progress", "0%");
      this.gauge.setAttribute("aria-valuenow", "0");
      this.gauge = null;
    }
  }

  private handleAudioError() {
    this.resetCurrent();
    this.onError(Messages.previewFailed);
  }
}
