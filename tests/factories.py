"""FactoryBoy factories for the database models.

Provide realistic `Song` and `SongFingerprint` instances for tests without
hard-coding fixture data; used by repository/service tests.
UUIDv7 ids are generated server-side by the `uuidv7()` default, so
factories leave `id` unset unless a caller overrides it. Audit columns
`created_at` / `updated_at` are also server-defaulted (`func.now()`)
and likewise omitted.
"""

import random

import factory
from faker import Faker

from genreguru.db.engine import make_scoped_session
from genreguru.db.models import AudioFormat, Song, SongFingerprint

fake = Faker()

# Unbound scoped session; configured per-test by the factory_session
# fixture in conftest.py via Session.configure(bind=engine).
sc_session = make_scoped_session()

# ISRC is exactly 12 chars: CC-XXX-YY-NNNNN (hyphens omitted). The
# CC+XXX prefix is sampled once per process; YY+NNNNN derive from the
# factory sequence so ISRCs are unique and reproducible.
_UPPERCASE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_UNIT_DIGITS = "0123456789"
_HEX = "0123456789abcdef"
_TWO = "".join(random.choices(_UPPERCASE_ALPHABET, k=2))
_THREE = "".join(random.choices(_UPPERCASE_ALPHABET + _UNIT_DIGITS, k=3))


def _deezer_preview_url() -> str:
    # 32-hexit long string
    md5 = "".join(random.choices(_HEX, k=32))

    path = "/".join([*md5[:3], "0"])
    acl = f"/api/1/1/{path}/{md5}.mp3"

    hmac = "".join(random.choices(_HEX, k=64))
    return (
        f"https://cdnt-preview.dzcdn.net{acl}"
        f"?hdnea=exp=1787634553~acl={acl}*"
        f"~data=user_id=0,application_id=42"
        f"~hmac={hmac}"
    )


class SongFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Build a Song instance; every field is valid without a live DB."""

    class Meta:
        """Factory metadata: model and session binding."""

        model = Song
        sqlalchemy_session = sc_session

    # Generate unique, well-formed values without needing a live DB.
    deezer_id = factory.Sequence(lambda n: 1_000_000 + n)
    isrc = factory.Sequence(lambda n: f"{_TWO}{_THREE}{n % 100:02d}{n // 100:05d}")
    title = factory.Faker("sentence", nb_words=4)
    artist = factory.Faker("name")
    album = factory.LazyAttribute(lambda _: random.choice([fake.catch_phrase(), None]))
    preview_url = factory.LazyAttribute(lambda _: _deezer_preview_url())
    duration = factory.LazyAttribute(lambda _: random.randint(60, 600))


class SongFingerprintFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Build a SongFingerprint instance linked to a Song."""

    class Meta:
        """Factory metadata: model and session binding."""

        model = SongFingerprint
        sqlalchemy_session = sc_session

    song = factory.SubFactory(SongFactory)
    spectral_centroid = factory.Faker("pyfloat", min_value=100.0, max_value=5000.0)
    rms = factory.Faker("pyfloat", min_value=0.0, max_value=1.0)
    spectral_bandwidth = factory.Faker("pyfloat", min_value=50.0, max_value=3000.0)
    spectral_contrast = factory.Faker("pyfloat", min_value=0.0, max_value=100.0)
    spectral_flatness = factory.Faker("pyfloat", min_value=0.0, max_value=1.0)
    spectral_rolloff = factory.Faker("pyfloat", min_value=100.0, max_value=8000.0)
    zero_crossing_rate = factory.Faker("pyfloat", min_value=0.0, max_value=1.0)
    mfcc = factory.Faker("pyfloat", min_value=-1000.0, max_value=1000.0)
    audio_format = factory.LazyAttribute(
        lambda _: random.choice(list(AudioFormat)).value
    )
    sample_rate = factory.LazyAttribute(lambda _: random.choice([22050, 44100]))
