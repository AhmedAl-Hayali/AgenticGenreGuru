"""Development environment settings.

Values come from the Hydra `django` and `db` dev groups
(`config/django/dev.yaml`, `config/db/dev.yaml`); nothing hard-coded here.
`GENREGURU_ENV` selects the dev groups in the compose helper.
"""

import os

os.environ.setdefault("GENREGURU_ENV", "dev")

from .base import *  # noqa: E402, F403
