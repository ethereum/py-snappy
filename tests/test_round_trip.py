from hypothesis import given, settings, strategies as st

from py_snappy import compress, decompress

MEGABYTE = 1000000


@given(value=st.binary(min_size=1, max_size=2 * MEGABYTE))
@settings(max_examples=1000)
def test_round_trip(value):
    intermediate = compress(value)
    result = decompress(intermediate)
    assert value == result
