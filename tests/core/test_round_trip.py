from hypothesis import given, settings

from py_snappy import compress, decompress

from tests.core.strategies import random_test_vectors_large_st


@given(value=random_test_vectors_large_st)
@settings(max_examples=10000)
def test_round_trip(value):
    intermediate = compress(value)
    result = decompress(intermediate)
    assert value == result
