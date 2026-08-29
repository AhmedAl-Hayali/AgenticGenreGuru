# Docstring Style Guide

**Standard**: Google Python Style Guide (docstring section)
**Enforcement**: Ruff `D` rules with `convention = "google"`
**Rendering**: pdoc with `--docformat google`

## Overview

All public modules, classes, functions, and methods MUST have docstrings. Docstrings are enforced by Ruff pydocstyle rules and rendered by pdoc for API reference generation.

## Configuration

### pyproject.toml

```toml
[tool.ruff.lint]
select = ["D"]  # pydocstyle

[tool.ruff.lint.pydocstyle]
convention = "google"
```

### pdoc

Set the docformat in the package `__init__.py`:

```python
__docformat__ = "google"
```

Run pdoc with Google-style parsing:

```bash
pdoc --docformat google genreguru
```

## Rules

### 1. Every public item MUST have a docstring

Ruff enforces:
- `D101` — Missing docstring in public class
- `D102` — Missing docstring in public method (includes `@staticmethod`, `@classmethod`, `@property` getters)
- `D103` — Missing docstring in public function

Private items (prefixed with `_`) are exempt. If a module uses `__all__`, Ruff still checks all public names — `__all__` does not suppress D101/D102/D103.

### 2. One-liner vs multi-line

**Use a one-liner** when the function is simple and self-explanatory:

```python
def get_config() -> DictConfig:
    """Load and return the composed Hydra configuration."""
```

**Use multi-line** when the function has parameters, returns a non-obvious value, raises exceptions, or performs complex logic:

```python
def extract_features(
    audio: np.ndarray,
    sample_rate: int,
) -> dict[Feature, np.ndarray]:
    """Extract 8 acoustic features, returning raw per-frame ndarrays.

    Computes spectral_centroid, rms, spectral_bandwidth, spectral_contrast,
    spectral_flatness, spectral_rolloff, zero_crossing_rate, and mfcc.
    Collapse each raw array to a scalar with ``collapse_features``.

    Args:
        audio: Mono audio signal array.
        sample_rate: Audio sampling rate in Hz.

    Returns:
        Dictionary mapping each ``Feature`` member to its raw per-frame
        ndarray.

    Raises:
        AudioProcessingError: If DSP extraction fails on the input audio.
    """
```

### 3. Summary line

- MUST be on the first line after the opening `"""`
- MUST be in imperative mood ("Load" not "Loads", "Extract" not "Extracts")
- MUST end with a period
- MUST fit on one line (Ruff `D200`)

### 4. Description (optional)

If the summary line is insufficient, add a blank line then a description paragraph (Ruff `D205` enforces the blank line). Use this to explain *why* or *how* when the *what* isn't enough.

### 5. Section ordering

When present, sections MUST appear in this order:

1. `Args` — Function/method parameters
2. `Returns` — Return value (omit if return type is `None`)
3. `Yields` — For generators only (omit if not a generator)
4. `Raises` — Exceptions that may be raised (omit if the function does not raise)
5. `Examples` — Usage examples (optional)

### 6. Args section

Types live in the function signature — repeating them in the docstring creates drift risk. Document only the semantics.

```python
"""
Args:
    param_name: Description of the parameter.
    optional_param: Description. Defaults to None.
"""
```

**Rules:**
- Each parameter on its own line
- Description starts on the same line as the parameter name
- Continuation lines indented 8 spaces from margin (4 spaces past the parameter name)
- Do NOT repeat type annotations in the description
- Mention default values for optional parameters in the description

### 7. Returns section

Omit the Returns section when the return type is `None`.

```python
"""
Returns:
    Description of the return value.
"""
```

For complex returns, use a named structure:

```python
"""
Returns:
    Dictionary mapping feature names to scalar values,
    with keys matching the 8 DSP feature identifiers.
"""
```

### 8. Raises section

Omit the Raises section if the function does not raise exceptions.

```python
"""
Raises:
    AudioProcessingError: If DSP extraction fails on the input audio.
    NetworkDisconnectedError: If all retry attempts fail.
"""
```

### 9. Code references

Use single backticks for inline code references (Markdown syntax):

```python
"""Load config from the `logging` group."""
```

NOT double backticks (reST syntax):

```python
"""Load config from ``logging`` group."""  # WRONG
```

### 10. Module-level docstrings

Place at the top of the file, before imports:

```python
"""Centralized logging configuration for `genreguru`.

Design authority: docs/001-song-fingerprint-engine/logging-report.md.
Consumes the Hydra `logging` config group via `genreguru.config`.
"""
```

### 11. Class-level docstrings

Place the docstring on the class, not on `__init__`. Google style uses the class docstring to document constructor parameters.

One-liner for simple classes:

```python
class NonErrorFilter(logging.Filter):
    """Pass only records below ERROR (DEBUG/INFO/WARNING)."""
```

Multi-line for classes with non-obvious behavior:

```python
class FingerprintContextAdapter(logging.LoggerAdapter):
    """Inject isrc/deezer_id/song_id/reused context via `extra`.

    This adapter automatically enriches log records with song identification
    fields, enabling structured logging across the fingerprint pipeline.
    """
```

### 12. Variable docstrings

Place on the line after the assignment:

```python
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
"""Path to the Hydra configuration directory."""
```

### 13. Property docstrings

Place the docstring on the getter, not the setter. The getter defines the property's semantics.

```python
@property
def is_active(self) -> bool:
    """Whether the fingerprint has been processed."""
    return self._is_active


@is_active.setter
def is_active(self, value: bool) -> None:
    self._is_active = value
```

## Examples

### Good

```python
def persist_fingerprint(
    session: Session,
    song: Song,
    fingerprint: dict[str, float],
) -> None:
    """Store a song fingerprint record linked to the given song.

    Args:
        session: Active SQLAlchemy database session.
        song: Persisted song record to link the fingerprint to.
        fingerprint: Map of feature names to scalar values.

    Raises:
        sqlalchemy.exc.IntegrityError: If a fingerprint already exists.
    """
```

```python
def is_valid_isrc(isrc: str) -> bool:
    """Check whether a string is a valid ISRC format."""
```

### Bad

```python
def persist_fingerprint(session, song, fingerprint):
    # No docstring — Ruff D102 violation
    pass
```

```python
def persist_fingerprint(session: Session, song: Song, fingerprint: dict) -> None:
    """Store a fingerprint.

    Args:
        session: The session.
        song: The song.
        fingerprint: The fingerprint dict with float values.

    Returns:
        None.
    """
    # Vague descriptions, redundant "None" return, redundant type info
```

```python
def persist_fingerprint(session: Session, song: Song, fingerprint: dict) -> None:
    """Store a fingerprint.

    Args:
        session (Session): The database session.  # WRONG — type in description
        song: The song record.
    """
```

## Ruff Rules Reference

| Rule | Description                                           | Status                             |
|------|-------------------------------------------------------|------------------------------------|
| D100 | Missing docstring in public module                    | Ignored for `__init__.py` only     |
| D101 | Missing docstring in public class                     | Enforced                           |
| D102 | Missing docstring in public method                    | Enforced                           |
| D103 | Missing docstring in public function                  | Enforced                           |
| D104 | Missing docstring in public package                   | Ignored                            |
| D200 | One-line docstring should fit on one line             | Enforced                           |
| D205 | 1 blank line required between summary and description | Enforced                           |
| D211 | No blank line required before class docstring         | Enforced (Google default)          |
| D212 | Multi-line docstring summary starts at first line     | Enforced (Google default)          |
| D401 | First line should be in imperative mood               | Enforced                           |
| D417 | Missing argument descriptions in docstring            | Enforced                           |
