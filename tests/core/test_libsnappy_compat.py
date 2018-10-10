from hypothesis import given, settings

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


from tests.core.strategies import (
    random_test_vectors_large_st,
    random_test_vectors_small_st,
)


#
# Round trip value -> compress() -> decompress()
#
@given(value=random_test_vectors_large_st)
@settings(max_examples=1000)
def test_local_decompress_libsnappy_compressed(value):
    intermediate = libsnappy_compress(value)
    result = decompress(intermediate)
    assert value == result


@given(value=random_test_vectors_large_st)
@settings(max_examples=1000)
def test_libsnappy_decompress_local_compressed(value):
    intermediate = compress(value)
    result = libsnappy_decompress(intermediate)
    assert value == result


LIB_SNAPPY_ERRORS = (CompressedLengthError, UncompressError)
PY_SNAPPY_ERRORS = (BaseSnappyError,)


def pass_fail(v):
    if v:
        return "pass"
    else:
        return "fail"


#
# Error cases
#
@given(value=random_test_vectors_small_st)
@settings(max_examples=100, deadline=None)  # takes a long time.
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
    elif not py_snappy_error and not lib_snappy_error:
        assert lib_result == py_result
    else:
        raise AssertionError(
            f"behavioral mismatch: py_snappy: {pass_fail(py_snappy_error)}  lib-snappy: {pass_fail(lib_snappy_error)}"  # noqa: E501
        )
