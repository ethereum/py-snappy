import pytest

from py_snappy import compress, decompress, CorruptError


def test_compress_empty_string():
    assert compress(b'') == b'\x00'


def test_decompress_empty_string():
    with pytest.raises(CorruptError):
        decompress(b'')
