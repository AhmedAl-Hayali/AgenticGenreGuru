"""Production environment settings.

Values come from the Hydra `django` and `db` prod groups
(`config/django/prod.yaml`, `config/db/prod.yaml`). Secrets resolve via
`${oc.env:...}` interpolation and fail fast at load when missing — no secrets
in the repo, nothing hard-coded here. `GENREGURU_ENV` selects the prod
groups in the compose helper.
"""

import os

os.environ.setdefault("GENREGURU_ENV", "prod")

from .base import *  # noqa: E402, F403
