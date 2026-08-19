"""Hydra configuration compose helper for the Django path."""

import os
from functools import lru_cache
from pathlib import Path

import hydra
from omegaconf import DictConfig

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


@lru_cache(maxsize=1)
def get_config(overrides: tuple[str, ...] | None = None) -> DictConfig:
    """Compose the active Hydra config via the compose API (Django-safe).

    `@hydra.main` is unsuitable for the Django path because it hijacks
    `argv` and changes the working directory; `initialize_config_dir`
    accepts an absolute config path so behavior is cwd-independent.

    The active environment (`GENREGURU_ENV`, default `dev`) selects the
    ``logging``, ``db``, and ``django`` config groups; the Django settings
    entry point (`development.py`/`production.py`/`test.py`) sets
    `GENREGURU_ENV` before importing the shared ``base`` settings. Extra
    overrides (e.g. `features=all`) can be passed per caller. Secrets in the
    YAML resolve via OmegaConf's native ``${oc.env:...}`` resolver.

    Args:
        overrides: Optional additional Hydra override strings.

    Returns:
        The composed Hydra configuration dictionary.
    """
    env = os.environ.get("GENREGURU_ENV", "dev")
    composed = (
        f"logging={env}",
        f"db={env}",
        f"django={env}",
    ) + (tuple(overrides) if overrides else ())
    with hydra.initialize_config_dir(config_dir=str(CONFIG_DIR)):
        cfg = hydra.compose(config_name="config", overrides=list(composed))
    return cfg
