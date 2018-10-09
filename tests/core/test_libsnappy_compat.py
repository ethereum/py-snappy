from hypothesis import given, settings, strategies as st

from py_snappy import compress, decompress, BaseSnappyError
from snappy import (
    compress as libsnappy_compress,
    decompress as libsnappy_decompress,
    UncompressError,
)

try:
    from snappy._snappy import CompressedLengthError
except ImportError:
    CompressedLengthError = None


MEGABYTE = 1000000


#
# Round trip value -> compress() -> decompress()
#
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


LIB_SNAPPY_ERRORS = (CompressedLengthError, UncompressError)
PY_SNAPPY_ERRORS = (BaseSnappyError,)


#
# Error cases
#
@given(value=st.binary(min_size=1, max_size=2 * MEGABYTE))
@settings(max_examples=1000, deadline=None)  # takes a long time.
def test_decompress_error_parity(value):
    try:
        py_result = decompress(value)
    except PY_SNAPPY_ERRORS:
        py_snappy_error = True
    else:
        py_snappy_error = False

    try:
        lib_result = libsnappy_decompress(value)
    except LIB_SNAPPY_ERRORS:
        lib_snappy_error = True
    else:
        lib_snappy_error = False

    if py_snappy_error and lib_snappy_error:
        pass
    if not py_snappy_error and not lib_snappy_error:
        assert lib_result == py_result
