"""Standalone core library: silent until an application configures logging."""

__docformat__ = "google"

import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
