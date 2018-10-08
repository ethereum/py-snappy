from hypothesis import given, settings, strategies as st

from py_snappy import compress, decompress
from snappy import compress as libsnappy_compress, decompress as libsnappy_decompress

MEGABYTE = 1000000


@given(value=st.binary(min_size=1, max_size=2 * MEGABYTE))
@settings(max_examples=1000)
def test_local_decompress_libsnappy_compressed(value):
    intermediate = libsnappy_compress(value)
    result = decompress(intermediate)
    assert value == result


@given(value=st.binary(min_size=1, max_size=2 * MEGABYTE))
@settings(max_examples=1000)
def test_libsnappy_decompress_local_compressed(value):
    intermediate = compress(value)
    result = libsnappy_decompress(intermediate)
    assert value == result
