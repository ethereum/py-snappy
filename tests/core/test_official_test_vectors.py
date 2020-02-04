from pathlib import Path

import pytest

from hypothesis import given, strategies as st, settings
import py_snappy
from py_snappy import BaseSnappyError, compress, decompress
from snappy import (
    compress as libsnappy_compress,
    decompress as libsnappy_decompress,
    UncompressError,
)


BASE_DIR = Path(py_snappy.__file__).resolve().parent.parent
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"


CACHE = {}


def load_fixture(fixture_name):
    if fixture_name not in CACHE:
        fixture_path = FIXTURES_DIR / fixture_name
        assert fixture_path.exists()
        assert fixture_path.is_file()
        CACHE[fixture_name] = fixture_path.read_bytes()
    return CACHE[fixture_name]


FIXTURES_TO_COMPRESS = (
    "alice29.txt",
    "asyoulik.txt",
    "fireworks.jpeg",
    "geo.protodata",
    "html",
    "html_x_4",
    "kppkn.gtb",
    "lcet10.txt",
    "paper-100k.pdf",
    "plrabn12.txt",
    "urls.10K",
)


fixture_st = st.sampled_from(FIXTURES_TO_COMPRESS).map(load_fixture)


@st.composite
def fixture_data(draw, fixture_st=fixture_st):
    fixture_bytes = draw(fixture_st)
    size = len(fixture_bytes)
    slice = draw(st.slices(size))
    return fixture_bytes[slice]


MAX_EXAMPLES = 100


@given(fixture_data=fixture_data())
@settings(max_examples=MAX_EXAMPLES, deadline=None)  # takes a long time.
def test_compression_round_trip_of_official_test_fixtures(fixture_data):
    intermediate = compress(fixture_data)
    actual = decompress(intermediate)
    assert fixture_data == actual


@given(fixture_data=fixture_data())
@settings(max_examples=MAX_EXAMPLES, deadline=None)  # takes a long time.
def test_decompress_libsnappy_compressed_test_fixture(fixture_data):
    intermediate = libsnappy_compress(fixture_data)
    actual = decompress(intermediate)
    assert fixture_data == actual


@given(fixture_data=fixture_data())
@settings(max_examples=MAX_EXAMPLES, deadline=None)  # takes a long time.
def test_libsnapp_decompress_compressed_test_fixture(fixture_data):
    intermediate = compress(fixture_data)
    actual = libsnappy_decompress(intermediate)
    assert fixture_data == actual


FIXTURES_TO_DECOMPRESS = ("baddata1.snappy", "baddata2.snappy", "baddata3.snappy")


@pytest.mark.parametrize("fixture_name", FIXTURES_TO_DECOMPRESS)
def test_decompression_of_official_corrupt_fixtures(fixture_name):
    fixture_data = load_fixture(fixture_name)
    with pytest.raises(BaseSnappyError):
        decompress(fixture_data)

    # now ensure that the canonical implementation errors too
    with pytest.raises(UncompressError):
        libsnappy_decompress(fixture_data)
