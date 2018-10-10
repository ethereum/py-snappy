from pathlib import Path

import pytest

import py_snappy
from py_snappy import BaseSnappyError, compress, decompress
from snappy import (
    compress as libsnappy_compress,
    decompress as libsnappy_decompress,
    UncompressError,
)


BASE_DIR = Path(py_snappy.__file__).resolve().parent.parent
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"


def load_fixture(fixture_name):
    fixture_path = FIXTURES_DIR / fixture_name
    assert fixture_path.exists()
    assert fixture_path.is_file()
    return fixture_path.read_bytes()


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


@pytest.mark.parametrize("fixture_name", FIXTURES_TO_COMPRESS)
def test_compression_round_trip_of_official_test_fixtures(fixture_name):
    fixture_data = load_fixture(fixture_name)
    intermediate = compress(fixture_data)
    actual = decompress(intermediate)
    assert fixture_data == actual


@pytest.mark.parametrize("fixture_name", FIXTURES_TO_COMPRESS)
def test_decompress_libsnappy_compressed_test_fixture(fixture_name):
    fixture_data = load_fixture(fixture_name)
    intermediate = libsnappy_compress(fixture_data)
    actual = decompress(intermediate)
    assert fixture_data == actual


@pytest.mark.parametrize("fixture_name", FIXTURES_TO_COMPRESS)
def test_libsnapp_decompress_compressed_test_fixture(fixture_name):
    fixture_data = load_fixture(fixture_name)
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
