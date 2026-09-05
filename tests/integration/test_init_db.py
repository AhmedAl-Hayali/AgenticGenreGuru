"""Integration tests for `genreguru.db.init_db` table creation.

Runs against the real PostgreSQL server composed by the Hydra `db`
group and doubles as the executable schema contract from
`data-model.md`: column types and nullability, native `uuidv7()`
defaults, uniqueness on `deezer_id`/`isrc` and `song_id`, and the
songs -> song_fingerprints FK. `init_db` failure modes (unreachable
database, pre-18 server) surface as errors here.

Schema isolation: each test recreates a dedicated `test` schema
(drop -> create -> check -> drop cascade), so DDL always lands in a
pristine namespace and nothing outside it is touched. The `test` name
is reserved for this suite; contents are destroyed every run.
"""

from collections import namedtuple

import pytest
from sqlalchemy import Inspector, inspect, text
from sqlalchemy.schema import CreateSchema, DropSchema

from genreguru.db import init_db
from genreguru.db.engine import create_engine

EXPECTED_TABLES = {"songs", "song_fingerprints"}
TEST_SCHEMA = "test"
MISSING_FKC_NAME = "ForeignKeyConstraintUnnamed"

ColumnInfo = namedtuple("ColumnInfo", ["type", "nullable", "default"])
FKCstrInfo = namedtuple("FKCstrInfo", ["referred_table", "referred_columns"])


@pytest.fixture()
def engine(db_cfg):
    """Function-scope engine pinned to a pristine `test` schema.

    Pin `SEARCHPATH` to  `public` (default) AND test schema on every pooled
    connection (survives reconnects), so unqualified DDL from
    `init_db.create_all_tables()` lands in `test`. The schema is recreated
    per test and cascade-dropped at teardown; other schemas are untouched.
    """
    eng = create_engine(db_cfg)

    with eng.begin() as conn:
        conn.execute(text(f"SET SEARCH_PATH TO {TEST_SCHEMA}"))
        conn.execute(DropSchema(TEST_SCHEMA, cascade=True, if_exists=True))
        conn.execute(CreateSchema(TEST_SCHEMA))
    try:
        yield eng
    finally:
        with eng.begin() as conn:
            conn.execute(DropSchema(TEST_SCHEMA, cascade=True, if_exists=True))
        eng.dispose()


@pytest.fixture()
def eng_inspector(engine) -> Inspector:
    """SQLAlchemy inspector scoped to the isolated `test` schema."""
    return inspect(engine)


def _table_names(inspector: Inspector) -> set[str]:
    return set(inspector.get_table_names(schema=TEST_SCHEMA))


def _foreign_key_constraints(eng_inspector: Inspector) -> dict[str, FKCstrInfo]:
    fk_cstrs = eng_inspector.get_foreign_keys("song_fingerprints", schema=TEST_SCHEMA)
    fk_cstrs = {
        fk_cstr["name"] or MISSING_FKC_NAME: FKCstrInfo(
            fk_cstr["referred_table"], fk_cstr["referred_columns"]
        )
        for fk_cstr in fk_cstrs
    }

    return fk_cstrs


def _columns(inspector: Inspector, table: str) -> dict[str, ColumnInfo]:
    """Map column name -> ColumnInfo(type, nullable, default)."""
    cols = inspector.get_columns(table, schema=TEST_SCHEMA)
    return {
        col["name"]: ColumnInfo(
            str(col["type"]).lower(), col["nullable"], col["default"]
        )
        for col in cols
    }


def _unique_constraint_targets(inspector: Inspector, table: str) -> set[str]:
    """Column names covered by UNIQUE constraints on the given table."""
    uq_cstrs = inspector.get_unique_constraints(table, schema=TEST_SCHEMA)
    # Potentially faulty in the future - currently only correctly captures *single*-column unique constraints
    cols: set[str] = set()
    for uc in uq_cstrs:
        cols.update(uc["column_names"])
    return cols


def test_all_tables_created_idempotently(engine, eng_inspector) -> None:
    """Test init_db creates every table and is rerun-safe (no error)."""
    init_db.create_all_tables(engine)
    init_db.create_all_tables(engine)  # idempotent rerun

    tables = _table_names(eng_inspector)
    assert tables == EXPECTED_TABLES


def test_schema_matches_data_model(engine, eng_inspector) -> None:
    """Test columns, uuidv7 defaults, uniques, and FK match data-model.md."""
    init_db.create_all_tables(engine)

    song_cols = _columns(eng_inspector, "songs")
    fp_cols = _columns(eng_inspector, "song_fingerprints")

    fp_metrics = [
        "spectral_centroid",
        "rms",
        "spectral_bandwidth",
        "spectral_contrast",
        "spectral_flatness",
        "spectral_rolloff",
        "zero_crossing_rate",
        "mfcc",
    ]
    for metric in fp_metrics:
        assert fp_cols[metric].type == "double precision"
        assert fp_cols[metric].nullable is False

    assert fp_cols["audio_format"].type == "varchar(4)"
    assert fp_cols["sample_rate"].type == "integer"

    assert song_cols["id"].type == "uuid"
    assert song_cols["deezer_id"].type == "bigint"
    assert song_cols["isrc"].type == "varchar(255)"
    assert song_cols["title"].type == "varchar(255)"
    assert song_cols["artist"].type == "varchar(255)"
    assert song_cols["album"].type == "varchar(255)"
    assert song_cols["album"].nullable is True
    assert song_cols["preview_url"].type == "text"
    assert song_cols["duration"].type == "integer"

    # Native server-side uuidv7() defaults (PG18+; data-model.md).
    assert song_cols["id"].default == "uuidv7()"
    assert fp_cols["id"].default == "uuidv7()"

    song_unique_cols = _unique_constraint_targets(eng_inspector, "songs")
    fp_unique_cols = _unique_constraint_targets(eng_inspector, "song_fingerprints")

    # Uniqueness: deezer_id + isrc in songs; song_id in song_fingerprints.
    assert {"deezer_id", "isrc"} <= song_unique_cols
    assert {"song_id"} <= fp_unique_cols

    fk_cstrs = _foreign_key_constraints(eng_inspector)
    # no unnamed foreign key constraints
    assert MISSING_FKC_NAME not in fk_cstrs
    # songs 1 -> 1 song_fingerprints via a real FK on songs.id.
    assert fk_cstrs["fk_song_fingerprints_song_id_songs"].referred_table == "songs"
    assert fk_cstrs["fk_song_fingerprints_song_id_songs"].referred_columns == ["id"]
