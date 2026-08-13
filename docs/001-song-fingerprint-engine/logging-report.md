# Logging Design Report: Song Fingerprint Engine

**Purpose**: Concrete logging design for `src/core/` derived from the article "From Print to Production: Best Practices for Python Logging" (Aliakbar Hosseinzadeh) plus project Constitution constraints (SRP per module, strict TDD, library-first architecture). Implementers MUST follow this report when executing `src/core/` tasks in [tasks.md](../../specs/001-song-fingerprint-engine/tasks.md).
**Created**: 2026-08-13
**Feature**: `001-song-fingerprint-engine`
**Applicable tasks**: T006, T007, T010, T011, T020-T025, T039, T044 (logging portions; configuration-management aspects live in [config-report.md](config-report.md))

---

## 1. Core Principles (from the article)

| #  | Rule                                                                                                   | Where enforced                                                                                        |
|----|--------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| 1  | Use stdlib `logging`, never `print()`                                                                  | All `src/core/` modules                                                                               |
| 2  | Configure once, centrally, via `dictConfig`                                                            | `src/core/logging.py` (T011)                                                                          |
| 3  | One named logger per module: `logger = logging.getLogger(__name__)`                                    | Every module                                                                                          |
| 4  | Handlers live on the root logger; child loggers propagate (no duplicate output)                        | `src/core/logging.py`                                                                                 |
| 5  | Multi-destination routing: stdout (non-errors), stderr (errors), JSONL file (all)                      | T011 handlers                                                                                         |
| 6  | Structured JSON in files, UTC ISO timestamps, `extra` context                                          | `JsonFormatter` (T011)                                                                                |
| 7  | Non-blocking I/O via `QueueHandler` + `QueueListener`                                                  | T011                                                                                                  |
| 8  | Lazy `%s`-style args, never f-strings in log calls                                                     | All modules                                                                                           |
| 9  | `logger.exception()` inside `except` blocks (full traceback)                                           | All modules                                                                                           |
| 10 | Log safely: no secrets, no PII, no binary payloads                                                     | All modules                                                                                           |
| 11 | Library code silent until configured: `NullHandler` on package root                                    | `src/core/__init__.py`                                                                                |
| 12 | No hard-coded logging constants; all levels/format/handlers come from the Hydra `logging` config group | `src/core/logging.py` + `config/logging/`; tree & conventions in [config-report.md](config-report.md) |

---

## 2. Configuration Hub — `src/core/logging.py` (T011)

### Layout

```text
src/core/logging.py          # setup_logging() loads Hydra `logging` group → dictConfig, install_queue_handler(), JsonFormatter, NonErrorFilter, RichHandler wiring, logger helpers
logs/                        # runtime artifacts (gitignored, created on first run)
config/logging/*.yaml        # dev/prod logging groups — see config-report.md for the full Hydra config tree
```

> **Config management**: the Hydra config tree, `defaults` composition, `@hydra.main` vs compose API, secrets via `${env:...}`, and the Python 3.14 `hydra-core` pin are documented in [config-report.md](config-report.md). This report covers how `src/core/logging.py` consumes the `logging` group.

### `setup_logging()` — build the `dictConfig` dict from the Hydra `logging` group

`setup_logging()` does NOT hard-code a Python dict. It loads the active logging configuration from the Hydra tree (`config/logging/dev.yaml` or `prod.yaml`, selected by the `defaults` list in `config/config.yaml`), converts it with `OmegaConf.to_container(cfg.logging, resolve=True)`, and feeds it to `logging.config.dictConfig`. Command-line overrides therefore reach the logging setup without touching code (e.g. `python -m src.core.db.init_db logging.level=DEBUG logging.file.maxBytes=10485760`).

Formatters:
- `console` text: `"%(levelname)s %(name)s %(message)s"`.
- `json` structured: custom `JsonFormatter` emitting one JSON object per line — `level`, `message`, `timestamp` (UTC ISO), `logger`, `module`, `function`, `line`, `thread_name`, plus every key supplied via `extra` (recommended `fmt_keys` mapping).

Handlers:
- `stdout`: `logging.StreamHandler` → `sys.stdout`, level `DEBUG`, formatter `console`, filtered by `NonErrorFilter` (passes only <ERROR).
- `stderr`: `logging.StreamHandler` → `sys.stderr`, level `ERROR`, formatter `console`.
- `file_all`: `RotatingFileHandler` → `logs/genreguru.log.jsonl`, level `DEBUG`, formatter `json`, `maxBytes` ≈ 10 MB, `backupCount` = 10, `encoding='utf-8'`, `delay=True`; parent dir `logs/` auto-created (SafeRotatingFileHandler).
- **Dev console (optional)**: in interactive/development runs, replace the two plain stream handlers with `RichHandler` instances — see "RichHandler — developer console output" below. This is gated by environment (e.g. `LOG_HANDLERS=rich`); it never replaces the JSONL file sink.

Root logger: level `DEBUG`, handlers `[stdout, stderr, file_all]` (or the Rich equivalents under dev mode). Set `disable_existing_loggers: False` so third-party (librosa, httpx, sqlalchemy, django) loggers stay live. Optionally lower `httpx`/`urllib3` to `WARNING` to reduce noise.

### `JsonFormatter` — structured JSONL records

A `logging.Formatter` subclass that renders each record as a single line of JSON (JSONL). It first runs the standard lazy `%-style` interpolation on the record's message, then assembles a fixed set of base fields: `level` (the human-readable level name), `message` (the interpolated text), `timestamp` (UTC, ISO-8601), `logger` (record name), `module`, `function` (function name), `line` (line number), and `thread_name`. Beyond these base fields, it supports an optional `fmt_keys` mapping: each entry maps a desired JSON field name to a record attribute (for example `isrc` → record attribute `isrc`, `deezer_id` → `deezer_id`, `reused` → `reused`). For every mapping entry the formatter reads the attribute off the record via a tolerant lookup — if the attribute is absent or `None`, the JSON field is simply omitted rather than raising a `KeyError`. This tolerance is what lets the `FingerprintContextAdapter` (below) attach `isrc`/`deezer_id`/`song_id`/`reused` on some records but not others without breaking the format. Finally the assembled dict is serialized to JSON with a fallback `default=str` coercion so that any non-serializable value present on a record (for example an exception object from a `logger.exception(...)` call) cannot crash the handler — it degrades to its string form instead.

### `NonErrorFilter` — stdout hygiene

A `logging.Filter` subclass whose `filter()` method returns true only for records whose numeric level is below `ERROR`, i.e. `DEBUG`, `INFO`, and `WARNING`. It is attached exclusively to the `stdout` handler so that errors and critical messages never pollute the normal console output stream: they are routed to `stderr` instead. The `stderr` and `file_all` handlers do not carry this filter, which is what guarantees the JSONL file still records every level while the console stays split (informational output on stdout, failures on stderr). Because it is declared as a named filter in the `dictConfig` dict (`"non_error"`), it can be reused by any handler added later without code changes.

### `RichHandler` — developer console output

Rich ships a logging handler (`rich.logging.RichHandler`) that colorizes and formats console output using ANSI escape codes and Rich's rendering engine, providing colored level labels, path + line info, word-wrapped output, and — with `rich_tracebacks=True` — syntax-highlighted, multi-context exception tracebacks that are considerably more readable than the stdlib traceback. It is configured in the `dictConfig` dict via `"class": "rich.logging.RichHandler"` with constructor keywords: `rich_tracebacks` (enable Rich Traceback rendering), `tracebacks_suppress` (a list of modules to hide from tracebacks — set it to Django itself so only application frames appear), `show_path`, `show_level`, `show_time`, `highlighter`, and `markup`.

Two details matter for integration with the rest of this design:

- **Markup is off by default.** Rich does not interpret Console Markup in log messages unless `markup=True` is set on the handler, because most libraries (including ours) are not careful to escape literal square brackets. The safe pattern is to leave `markup=False` globally and opt in per message via `extra={"markup": True}` only where a hand-authored, deliberately formatted message is emitted. The highlighter can likewise be overridden per message with `extra={"highlighter": None}`.
- **Rich output is ANSI-colored, not structured.** It is a human-facing dev artifact, not a machine/aggregator format. Therefore the Rich console handlers are driven by the `logging.dev.rich` YAML flag (enabled in the `dev` config group, `false` in `prod`; never enabled in `python -m src.core.db.init_db` or CI where plain `console` text is expected), and they operate strictly as the console pair — one RichHandler writing to `sys.stdout` carrying the `non_error` filter, one writing to `sys.stderr` at `ERROR` — preserving the stdout/stderr split while leaving the rotating JSONL `file_all` handler untouched as the canonical structured sink for production observability.

Because Rule 9 already mandates `logger.exception(...)` in every `except` block, Rich's `rich_tracebacks=True` renders those records with full highlighted frames for free; no additional exception handling is required in application code. Add `rich` to `pyproject.toml` runtime dependencies (task T002) and wire the handler selection inside `setup_logging()` (task T011).

### `install_queue_handler()` — non-blocking fan-out

After `dictConfig`, wrap the root handlers behind a named `QueueHandler` (`logging.handlers.QueueHandler` over `queue.SimpleQueue()`), name it `"queue_handler"` for `logging.getHandlerByName(...)`, and start a `QueueListener` (`respect_handler_level=True`). This keeps audio fetch + DSP on the request path non-blocking and scales with any future HTTP/syslog sink added to the same dict. Call `setup_logging()` once at the app entrypoint (Django `settings.py`/`manage.py`, or `__main__` of standalone `python -m` scripts); never call `basicConfig()` afterward.

### `NullHandler` for standalone-library safety

Attach `logging.NullHandler()` to the `src.core` package logger in `src/core/__init__.py` so the core library emits nothing until an application configures it (Constitution Principle I — headless CLI / test isolation).

### `FingerprintContextAdapter` — the `reused` flag

- Export a `LoggerAdapter` that injects `isrc`, `deezer_id`, `song_id`, `reused` fields via `extra` automatically.
- Contract requirement (`contracts/search-api.md` §2): the confirm path MUST log `reused=true` when fingerprint reused from the DB, `reused=false` when freshly generated; the caller is NOT informed — logging is the only distinction.
- Helper: `log_fingerprint_outcome(isrc, deezer_id, song_id, reused, elapsed)` wrapping a single INFO call through the adapter.

### Context-vs-secrets rule

Never emit the `DATABASE_URL` password, Deezer/OAuth tokens, full binary audio, or PII through any formatter.

---

## 3. Per-Module Logging Requirements

### T006 — `src/core/errors.py`

- Exceptions carry machine-readable attrs (e.g. `isrc`, `deezer_id`, `code`, `attempts`) so catch sites populate `extra` via the adapter without string parsing.
- No `logging` calls inside exception classes (SRP; logged at the raise/catch boundary).

### T007 — `src/core/db/engine.py`

- INFO once on engine init: host, database name, pool size, dialect — **never the password** (lazy args).
- DEBUG on session open/close (created via context/factory).
- WARNING on pool exhaustion or disconnect/reconnect events.
- Do not enable `echo=True` logging by default; expose it only via env-gated DEBUG.

### T010 — `src/core/db/init_db.py`

- Standalone `python -m src.core.db.init_db` entrypoint: call `setup_logging()` in `__main__`.
- INFO: table-creation start + completion with created-table count.
- ERROR: `logger.exception` on migration/DDL failure, re-raise.

### T020 — `src/core/audio/loader.py`

- DEBUG: source reference, `sample_rate`, channel count, duration, detected format, and "downmixed to mono" event.
- ERROR + `logger.exception` → raises `AudioProcessingError` (`"audio file cannot be processed"`, REQ-015).
- Lazy formatting only; log the audio path/ref, never the decoded buffer.

### T021 — `src/core/audio/features.py`

- DEBUG: input frame shape/sample-rate per feature computation and each collapsed arithmetic-mean scalar.
- WARNING/INFO: zero/low-energy frames (silent / non-musical input) — still produce a valid vector, do not fail (spec edge case).
- INFO on extraction completion with elapsed time (supports SC-002 <10 s).

### T022 — `src/core/deezer/client.py`

- INFO: outbound search `query` + `limit=5`, and response `total`.
- DEBUG: counts only (results returned, fields parsed) — never dump the full JSON payload.
- WARNING: Deezer error codes `QUOTA`(4) / `SERVICE_BUSY`(700) before entering the retry/backoff path.
- ERROR + `logger.exception` with `extra={isrc, deezer_id}`:
  - missing `isrc` → raise `MissingISRCError` (REQ-012, REQ-016)
  - missing/empty `preview` → raise `PreviewUnavailableError` (REQ-017); track NOT persisted, no snippet fetch
- INFO on `DATA_NOT_FOUND`(800) → empty matches (not an error).

### T023 — `src/core/deezer/snippets.py`

- INFO: fetch start and success (`bytes`, `elapsed`).
- WARNING per retry: `attempt=1..3`, `delay=5s`, exception reason (REQ-013).
- ERROR + `logger.exception` after the 3rd failed attempt → raises `NetworkDisconnectedError` (REQ-014).
- Never log byte content.

### T024 — `src/core/db/repositories.py`

- INFO: `find_by_isrc` outcome (`hit`/`miss` + `isrc`).
- INFO: insert of `song_id`/`isrc`/`deezer_id` for a new fingerprint row.
- WARNING: concurrent same-`isrc` write hitting the DB unique constraint (api_flow §3.2) — surface, do not duplicate.

### T025 — `src/core/fingerprint_service.py`

- The orchestration seam: use `FingerprintContextAdapter` (T011).
- INFO `reused=true`: `"fingerprint reused (isrc=%s song_id=%s)"`.
- INFO `reused=false`: `"fresh fingerprint generated (isrc=%s elapsed=%.2fs song_id=%s)"`.
- `logger.exception` before re-raising `AudioProcessingError` / `NetworkDisconnectedError` (REQ-014/REQ-015 propagation to UI).
- Always include elapsed time to correlate SC-002 (fresh gen volatile path) vs SC-005 (<500 ms reuse path).

### T039 — `src/core/audio/visualization.py`

- INFO: visualization data generated for `song_id`.
- DEBUG: spectrogram parameters (window, hop, FFT size, shape) — never log the spectrogram/matrix array.

### T044 — `src/core/recommendations.py`

- INFO: top-N result count + similarity scores.
- WARNING: fewer candidates than requested N, or degenerate (all-zero) modified query vector.

---

## 4. Cross-Cutting Conventions

1. `logger = logging.getLogger(__name__)` at module top of every `src/core/` file.
2. Lazy `%s`/`%d` args everywhere — arguments evaluated only if the record is emitted (matters in hot DSP loops).
3. `logger.exception(...)` inside `except` blocks (stack trace attached); plain `logger.error` without `exc_info` only when no exception is live.
4. Structured context via `extra` mapped by `JsonFormatter.fmt_keys`; formatter must tolerate records missing optional keys (guard `KeyError`).
5. No `basicConfig()` in library modules; single config site (`setup_logging`).
6. No secrets/tokens/passwords/PII/binary content in any log record.
7. `reused=true/false` (REQ-008 confirm path) emitted only through the T011 adapter so the field is always present in JSON.

---

## 5. Tests (TDD note)

Per Constitution III, logging behavior is unit-tested alongside each module's behavior — e.g. increasing a module's log level to DEBUG, calling a path, and asserting the emitted record's message + `extra` keys. Tests run against `caplog`/`pytest` `LogCaptureFixture`; no production handler output is asserted.

---

## 6. Traceability

| Design element                                            | Source                                                                                                     |
|-----------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| Reused-flag logging requirement                           | [search-api.md](../../specs/001-song-fingerprint-engine/contracts/search-api.md) §2                        |
| Network retry logging (3x/5s)                             | spec REQ-013 / REQ-014                                                                                     |
| Audio-processing error logging                            | spec REQ-015                                                                                               |
| Missing ISRC / preview fail-loud logging                  | spec REQ-012, REQ-016, REQ-017                                                                             |
| Perf timing fields (SC-002 / SC-005)                      | spec Success Criteria; [search-api.md](../../specs/001-song-fingerprint-engine/contracts/search-api.md) §3 |
| No secrets / clean library boundary                       | Constitution Principle I, IV                                                                               |
| Hydra config-driven logging (`logging` group consumption) | [config-report.md](config-report.md) (authoritative config-management source)                              |

**Source article**: "From Print to Production: Best Practices for Python Logging" (https://medium.com/@aliakbarhosseinzadeh/from-print-to-production-best-practices-for-python-logging-c4e8de2fa665). See [config-report.md](config-report.md) for configuration-management sources.