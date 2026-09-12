"""Unit tests for the shared exception hierarchy (`genreguru/errors.py`).

`GenreguruError.context()` extracts the machine-readable structured attributes
(isrc/deezer_id/code/attempts) for log `extra` enrichment; every attribute set
must survive, every `None` must be omitted, and subclasses must inherit the
same extraction unchanged.
"""

import pytest

from genreguru.errors import (
    GenreguruError,
    NetworkDisconnectedError,
)


class TestGenreguruErrorContext:
    """Pin `GenreguruError.context()` structured-attribute extraction."""

    # Coverage-redundant, but testing different structures for completeness
    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            (
                {"isrc": "GBDUW0000059", "deezer_id": 3135556},
                {"isrc": "GBDUW0000059", "deezer_id": 3135556},
            ),
            ({"code": 0, "attempts": 0}, {"code": 0, "attempts": 0}),
            ({}, {}),
        ],
        ids=["isrc_and_deezer_id", "falsy_but_set_kept", "no_attrs"],
    )
    def test_context_keeps_only_set_attrs(self, kwargs, expected):
        """`context()` must include every set attribute and omit None values."""
        assert GenreguruError("boom", **kwargs).context() == expected

    def test_subclass_passthrough(self):
        """A subclass must inherit the same context extraction."""
        assert NetworkDisconnectedError("boom", attempts=1).context() == {"attempts": 1}
