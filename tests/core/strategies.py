from hypothesis import strategies as st


MEGABYTE = 1000000
KILOBYTE = 1000

random_bytes_large_st = st.binary(min_size=0, max_size=2 * MEGABYTE)
random_bytes_small_st = st.binary(min_size=0, max_size=KILOBYTE)

contiguous_bytes_st = st.tuples(
    st.binary(min_size=1, max_size=1), st.integers(min_value=2, max_value=1024)
).map(lambda v: v[0] * v[1])

pattern_bytes_st = st.tuples(
    st.binary(min_size=1, max_size=128), st.integers(min_value=2, max_value=32)
).map(lambda v: v[0] * v[1])

random_bytes_with_pattern_blocks_st = st.lists(
    st.one_of(random_bytes_small_st, contiguous_bytes_st, pattern_bytes_st), max_size=20
).map(lambda v: b"".join(v))


random_test_vectors_large_st = st.one_of(
    random_bytes_large_st, random_bytes_with_pattern_blocks_st
)


random_test_vectors_small_st = st.one_of(
    random_bytes_small_st, random_bytes_with_pattern_blocks_st
)
