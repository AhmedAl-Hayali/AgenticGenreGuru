// Unit tests for the PreviewPlayer (fingerprint_app/ts/preview-player.ts).
// The player drives one shared medium, so tests inject a fake audio element
// (jsdom's HTMLMediaElement.play/pause are stubs) and assert the toggle/stop
// contract: lazy creation, same-row stop, switching rows, natural end, media
// errors, and play() rejection. The progress gauge contract (driven by a
// requestAnimationFrame loop, resets on stop/end/switch/error) and the
// previewProgress pure
// function live here too.

import { describe, expect, it, vi } from "vitest";
import { PreviewPlayer, previewProgress } from "../fingerprint_app/ts/preview-player.ts";
import { Messages } from "../fingerprint_app/ts/messages.ts";
import { MATCH } from "./helpers.ts";
import type { PreviewControl } from "../fingerprint_app/ts/render.ts";
import { installAnimationFrame } from "./setup.ts";

/** Fake HTMLMediaElement exposing play/pause that the injected factory returns. */
function fakeAudio(): {
  el: HTMLAudioElement;
  emit: (type: string) => void;
  setMedia: (current: number, duration: number) => void;
  play: ReturnType<typeof vi.fn>;
  pause: ReturnType<typeof vi.fn>;
} {
  const listeners: Record<string, Array<() => void>> = {};
  let paused = true;

  const play = vi.fn(() => {
    paused = false;
    return Promise.resolve();
  });
  const pause = vi.fn(() => {
    paused = true;
  });

  const media = {
    preload: "",
    src: "",
    currentTime: 0,
    duration: 0,
    get paused() {
      return paused;
    },
    play,
    pause,
    addEventListener: (type: string, fn: () => void) => {
      (listeners[type] ??= []).push(fn);
    },
    removeAttribute: () => {},
  };
  const el = media as unknown as HTMLAudioElement;

  const setMedia = (current: number, duration: number) => {
    media.currentTime = current;
    media.duration = duration;
  };

  const emit = (type: string) => {
    if (type === "ended") {
      paused = true;
    }
    for (const fn of listeners[type] ?? []) {
      fn();
    }
  };

  return { el, emit, setMedia, play, pause };
}

function makeButton(label = 'Preview "Harder, Better, Faster, Stronger"') {
  const button = document.createElement("button");
  button.setAttribute("aria-label", label);
  return button;
}

function makeGauge() {
  const gauge = document.createElement("div");
  gauge.setAttribute("role", "progressbar");
  gauge.setAttribute("aria-valuemin", "0");
  gauge.setAttribute("aria-valuemax", "100");
  gauge.setAttribute("aria-valuenow", "0");
  return gauge;
}

function makeControl(label?: string): PreviewControl {
  return { button: makeButton(label), gauge: makeGauge(), element: document.createElement("div") };
}

function expectIdle(button: HTMLButtonElement) {
  expect(button.classList.contains("playing")).toBe(false);
  expect(button.hasAttribute("aria-pressed")).toBe(false);
}

function primeGauge(player: PreviewPlayer) {
  const raf = installAnimationFrame();
  const control = makeControl();
  player.toggle(MATCH, control);
  return { control, raf };
}

function boot(
  overrides: {
    onError?: (message: string) => void;
    rejectPlay?: boolean;
    throwPlay?: boolean;
  } = {},
) {
  const audio = fakeAudio();
  if (overrides.rejectPlay) {
    audio.play.mockImplementation(() => Promise.reject(new Error("play failed")));
  }
  if (overrides.throwPlay) {
    audio.play.mockImplementation(() => {
      throw new Error("play threw synchronously");
    });
  }
  const onError = vi.fn(overrides.onError ?? (() => {}));
  const player = new PreviewPlayer({ createAudio: () => audio.el, onError });
  return { audio, player, onError };
}

describe("PreviewPlayer", () => {
  it("creates the medium lazily, sets the src, and starts playback on first toggle", () => {
    const { audio, player } = boot();
    const control = makeControl();

    player.toggle(MATCH, control);

    expect(audio.el.preload).toBe("none");
    expect(audio.el.src).toBe(MATCH.preview);
    expect(audio.play).toHaveBeenCalledTimes(1);
    expect(control.button.classList.contains("playing")).toBe(true);
    expect(control.button.getAttribute("aria-pressed")).toBe("true");
    expect(control.button.getAttribute("aria-label")).toBe(Messages.previewStopLabel(MATCH.title));
  });

  it("reuses the single shared medium across rows", () => {
    const { audio, player } = boot();
    const first = makeControl();
    const second = makeControl('Preview "Second"');

    player.toggle(MATCH, first);
    player.toggle({ ...MATCH, title: "Second" }, second);

    expect(audio.el.src).toBe(MATCH.preview);
    expect(audio.play).toHaveBeenCalledTimes(2);
  });

  it("stops when the active row's button is toggled again and restores its standby label", () => {
    const { audio, player } = boot();
    const control = makeControl();

    player.toggle(MATCH, control);
    player.toggle(MATCH, control);

    expect(audio.pause).toHaveBeenCalledTimes(1);
    expectIdle(control.button);
    expect(control.button.getAttribute("aria-label")).toContain("Preview");
    expect(control.button.getAttribute("aria-label")).not.toContain("Stop preview");
  });

  it("resets the previous button when switching to another row", () => {
    const { player } = boot();
    const first = makeControl();
    const second = makeControl('Preview "Second"');

    player.toggle(MATCH, first);
    player.toggle({ ...MATCH, title: "Second" }, second);

    expect(first.button.classList.contains("playing")).toBe(false);
    expect(first.button.getAttribute("aria-label")).not.toContain("Stop preview");
    expect(second.button.classList.contains("playing")).toBe(true);
  });

  it("resets the active row when the preview ends naturally and replays on a fresh toggle", () => {
    const { audio, player } = boot();
    const control = makeControl();

    player.toggle(MATCH, control);
    audio.emit("ended");

    expectIdle(control.button);

    player.toggle(MATCH, control);
    expect(audio.play).toHaveBeenCalledTimes(2);
    expect(control.button.classList.contains("playing")).toBe(true);
    expect(control.button.getAttribute("aria-pressed")).toBe("true");
  });

  it("reports a media error and resets the active button", () => {
    const { audio, player, onError } = boot();
    const control = makeControl();

    player.toggle(MATCH, control);
    audio.emit("error");

    expect(onError).toHaveBeenCalledWith(Messages.previewFailed);
    expectIdle(control.button);
  });

  it("reports a rejected play() and resets the active button", async () => {
    const { player, onError } = boot({ rejectPlay: true });
    const control = makeControl();

    player.toggle(MATCH, control);

    await vi.waitFor(() => {
      expect(onError).toHaveBeenCalledWith(Messages.previewFailed);
    });
    expect(control.button.classList.contains("playing")).toBe(false);
  });

  it("reports a synchronous play() throw and resets the active button", () => {
    const { audio, player, onError } = boot({ throwPlay: true });
    const control = makeControl();

    player.toggle(MATCH, control);

    expect(audio.play).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(Messages.previewFailed);
    expectIdle(control.button);
  });

  it("ignores a media error when no preview is active", () => {
    const { audio, player, onError } = boot();
    const control = makeControl();

    player.toggle(MATCH, control);
    player.stop();
    audio.emit("error");

    expect(onError).not.toHaveBeenCalled();
  });

  it("ignores a stale play() rejection once another row took over", async () => {
    const { audio, player, onError } = boot();
    const first = makeControl();
    const second = makeControl('Preview "Second"');
    let rejectLater!: (reason: unknown) => void;
    const slowPlay = new Promise<unknown>((_resolve, reject) => {
      rejectLater = reject;
    });
    audio.play.mockImplementationOnce(() => slowPlay).mockImplementation(() => Promise.resolve());

    player.toggle(MATCH, first);
    player.toggle({ ...MATCH, title: "Second" }, second);
    rejectLater(new Error("stale fail"));

    await vi.waitFor(() => {
      expect(onError).not.toHaveBeenCalled();
    });
    expect(second.button.classList.contains("playing")).toBe(true);
    expect(first.button.classList.contains("playing")).toBe(false);
    expect(audio.play).toHaveBeenCalledTimes(2);
  });

  it("ignores a toggle on a match without a preview", () => {
    const { audio, player, onError } = boot();
    const control = makeControl();
    const noPreview = { ...MATCH, preview: "" };

    player.toggle(noPreview, control);

    expect(audio.el.src).toBe("");
    expect(audio.play).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
    expect(control.button.classList.contains("playing")).toBe(false);
  });

  it("stop() pauses and clears the active row even when it is not the toggled row", () => {
    const { audio, player } = boot();
    const control = makeControl();

    player.toggle(MATCH, control);
    player.stop();

    expect(audio.pause).toHaveBeenCalledTimes(1);
    expectIdle(control.button);
  });

  it("stop() is a no-op when nothing is playing", () => {
    const { audio, player } = boot();

    player.stop();

    expect(audio.pause).not.toHaveBeenCalled();
  });

  it("tolerates a button without a standby label", () => {
    const { player } = boot();
    const bare = document.createElement("button");

    player.toggle(MATCH, {
      button: bare,
      gauge: makeGauge(),
      element: document.createElement("div"),
    });
    expect(bare.classList.contains("playing")).toBe(true);

    player.stop();
    expect(bare.getAttribute("aria-label")).toBe("");
    expect(bare.classList.contains("playing")).toBe(false);
  });

  it("falls back to a real audio factory and a no-op error handler when built without options", () => {
    const player = new PreviewPlayer();
    const control = makeControl();

    expect(() => player.toggle(MATCH, control)).not.toThrow();
    expect(control.button.classList.contains("playing")).toBe(true);
    player.stop();
    expect(control.button.classList.contains("playing")).toBe(false);
  });
});

describe("preview progress gauge", () => {
  it("fills the gauge and reports the percentage as time progresses", () => {
    const { audio, player } = boot();
    const { control, raf } = primeGauge(player);

    audio.setMedia(15, 30);
    raf.tick();

    expect(control.gauge.style.getPropertyValue("--preview-progress")).toBe("50%");
    expect(control.gauge.getAttribute("aria-valuenow")).toBe("50");
  });

  it("advances the bar on every frame, not only on sparse timeupdate events", () => {
    const { audio, player } = boot();
    const { control, raf } = primeGauge(player);

    audio.setMedia(7.5, 30);
    raf.tick();
    audio.setMedia(9, 30);
    raf.tick();

    expect(control.gauge.style.getPropertyValue("--preview-progress")).toBe("30%");
    expect(control.gauge.getAttribute("aria-valuenow")).toBe("30");
  });

  it("caps the reported progress at the preview's real duration", () => {
    const { audio, player } = boot();
    const { control, raf } = primeGauge(player);

    audio.setMedia(40, 30);
    raf.tick();

    expect(control.gauge.style.getPropertyValue("--preview-progress")).toBe("100%");
    expect(control.gauge.getAttribute("aria-valuenow")).toBe("100");
  });

  it("shows zero progress for an unknown duration", () => {
    const { audio, player } = boot();
    const { control, raf } = primeGauge(player);

    audio.setMedia(0, 0);
    raf.tick();

    expect(control.gauge.style.getPropertyValue("--preview-progress")).toBe("0%");
    expect(control.gauge.getAttribute("aria-valuenow")).toBe("0");
  });

  it("only rewrites aria-valuenow when the rounded percentage changes", () => {
    const { audio, player } = boot();
    const { control, raf } = primeGauge(player);
    const setAttribute = vi.spyOn(control.gauge, "setAttribute");

    audio.setMedia(5, 30);
    raf.tick(); // 16.67% -> 17
    audio.setMedia(5.9, 30);
    raf.tick(); // 19.67% -> 20
    audio.setMedia(6, 30);
    raf.tick(); // 20% -> 20, unchanged

    const ariaWrites = setAttribute.mock.calls.filter(([name]) => name === "aria-valuenow");
    expect(ariaWrites).toHaveLength(2);
  });

  it("cancels the frame loop and ignores progress once the preview is stopped", () => {
    const { audio, player } = boot();
    const { control, raf } = primeGauge(player);

    audio.setMedia(15, 30);
    raf.tick();
    player.stop();
    audio.setMedia(20, 30);
    raf.tick();

    expect(raf.cancel).toHaveBeenCalled();
    expect(control.gauge.style.getPropertyValue("--preview-progress")).toBe("0%");
    expect(control.gauge.getAttribute("aria-valuenow")).toBe("0");
  });

  it("cancels the frame loop when the preview errors and resets the gauge", () => {
    const { audio, player, onError } = boot();
    const { control, raf } = primeGauge(player);

    audio.setMedia(15, 30);
    raf.tick();
    audio.emit("error");

    expect(onError).toHaveBeenCalledWith(Messages.previewFailed);
    expect(raf.cancel).toHaveBeenCalled();
    expect(control.gauge.style.getPropertyValue("--preview-progress")).toBe("0%");
    expect(control.gauge.getAttribute("aria-valuenow")).toBe("0");
  });

  it("cancels the prior loop and zeroes its gauge when another row starts", () => {
    const { audio, player } = boot();
    const { control: first, raf } = primeGauge(player);
    const second = makeControl('Preview "Second"');

    audio.setMedia(15, 30);
    raf.tick();
    player.toggle({ ...MATCH, title: "Second" }, second);

    expect(raf.cancel).toHaveBeenCalled();
    expect(first.gauge.style.getPropertyValue("--preview-progress")).toBe("0%");
    expect(first.gauge.getAttribute("aria-valuenow")).toBe("0");
  });
});

describe("previewProgress", () => {
  it("measures the played fraction as a rounded percentage", () => {
    expect(previewProgress(0, 30)).toBe(0);
    expect(previewProgress(15, 30)).toBe(50);
    expect(previewProgress(30, 30)).toBe(100);
  });

  it("clamps out-of-range values", () => {
    expect(previewProgress(-5, 30)).toBe(0);
    expect(previewProgress(45, 30)).toBe(100);
  });

  it("returns zero for a missing or non-finite duration or position", () => {
    expect(previewProgress(10, 0)).toBe(0);
    expect(previewProgress(10, -1)).toBe(0);
    expect(previewProgress(10, Number.NaN)).toBe(0);
    expect(previewProgress(Number.NaN, 30)).toBe(0);
    expect(previewProgress(10, Number.POSITIVE_INFINITY)).toBe(0);
  });
});
