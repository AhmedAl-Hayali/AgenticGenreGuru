"""Standalone core library: silent until an application configures logging."""

import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
