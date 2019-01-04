# Based on https://github.com/StalkR/misc/commit/ba67f5e94d1b1c2cd550cf310b716c0a8101d7a0#diff-78a5f46979e1e7a85d116872e2c865d4  # noqa: E501
import functools
import itertools
from typing import Any, Callable, Iterable, Tuple, TypeVar

from .constants import TAG_LITERAL, TAG_COPY1, TAG_COPY2, TAG_COPY4
from .exceptions import BaseSnappyError, CorruptError, TooLargeError


# Each encoded block begins with the varint-encoded length of the decoded data,
# followed by a sequence of chunks. Chunks begin and end on byte boundaries.
# The first byte of each chunk is broken into its 2 least and 6 most
# significant bits called l and m: l ranges in [0, 4) and m ranges in [0, 64).
# l is the chunk tag. Zero means a literal tag. All other values mean a copy
# tag.
#
# For literal tags:
#   - If m < 60, the next 1 + m bytes are literal bytes.
#   - Otherwise, let n be the little-endian unsigned integer denoted by the
#     next m - 59 bytes. The next 1 + n bytes after that are literal bytes.
#
# For copy tags, length bytes are copied from offset bytes ago, in the style of
# Lempel-Ziv compression algorithms. In particular:
#   - For l == 1, the offset ranges in [0, 1<<11) and the length in [4, 12).
#     The length is 4 + the low 3 bits of m. The high 3 bits of m form bits
#     8-10 of the offset. The next byte is bits 0-7 of the offset.
#   - For l == 2, the offset ranges in [0, 1<<16) and the length in [1, 65).
#     The length is 1 + m. The offset is the little-endian unsigned integer
#     denoted by the next 2 bytes.
#   - For l == 3, this tag is a legacy format that is no longer supported.


def uint8(n: int) -> int:
    return n & ((1 << 8) - 1)


def uint32(n: int) -> int:
    return n & ((1 << 32) - 1)


def uint64(n: int) -> int:
    return n & ((1 << 64) - 1)


def uvarint(buf: bytes) -> Tuple[int, int]:
    """
    uvarint decodes a uint64 from buf and returns that value and the number of
    bytes read (> 0). If an error occurred, the value is 0 and the number of
    bytes n is <= 0 meaning:
    n == 0: buf too small
    n  < 0: value larger than 64 bits (overflow)
            and -n is the number of bytes read"""
    value, num_bytes_read = 0, 0
    for buf_pos, current_byte in enumerate(buf):
        if current_byte < 0x80:
            if buf_pos > 9 or (buf_pos == 9 and current_byte > 1):
                return 0, -1 * (buf_pos + 1)  # overflow
            return value | uint64(current_byte) << num_bytes_read, buf_pos + 1
        value |= uint64(current_byte & 0x7F) << num_bytes_read
        num_bytes_read += 7
    return 0, 0


TReturn = TypeVar("TReturn")


def bytes_gen(fn: Callable[..., Iterable[int]]) -> Callable[..., bytes]:
    @functools.wraps(fn)
    def inner(*args: Any, **kwargs: Any) -> bytes:
        return bytes(fn(*args, **kwargs))

    return inner


def tuple_gen(
    fn: Callable[..., Iterable[TReturn]]
) -> Callable[..., Tuple[TReturn, ...]]:
    @functools.wraps(fn)
    def inner(*args: Any, **kwargs: Any) -> Iterable[TReturn]:
        return tuple(fn(*args, **kwargs))

    return inner


@bytes_gen
def putuvarint(x: int) -> Iterable[int]:
    """
    putuvarint encodes a uint64.
    """
    while x >= 0x80:
        yield uint8(x) | 0x80
        x >>= 7
    yield x


def extract_meta(src: bytes) -> Tuple[int, int]:
    """
    Return a 2-tuple:

    - the length of the decoded block
    - the number of bytes that the length header occupied.
    """
    value, num_bytes = uvarint(src)
    if num_bytes <= 0 or value > 0xFFFFFFFF:
        raise CorruptError
    if value > 0x7FFFFFFF:
        raise TooLargeError
    return value, num_bytes


def decompress(buf: bytes) -> bytes:
    """
    decompress returns the decompressed form of buf.
    """
    block_length, length_header_size = extract_meta(buf)
    src = tuple(c for c in buf)
    src_len = len(src)
    dst = [0] * block_length
    d, offset, length = 0, 0, 0

    while length_header_size < src_len:
        elem_type = src[length_header_size] & 0x03
        if elem_type == TAG_LITERAL:
            literal_length = src[length_header_size] >> 2

            if literal_length < 60:
                length_header_size += 1
            elif literal_length == 60:
                length_header_size += 2
                if length_header_size > src_len:
                    raise CorruptError
                literal_length = src[length_header_size - 1]
            elif literal_length == 61:
                length_header_size += 3
                if length_header_size > src_len:
                    raise CorruptError
                literal_length = src[length_header_size - 2] | (
                    src[length_header_size - 1] << 8
                )
            elif literal_length == 62:
                length_header_size += 4
                if length_header_size > src_len:
                    raise CorruptError
                literal_length = (
                    src[length_header_size - 3]
                    | (src[length_header_size - 2] << 8)  # noqa: W503
                    | (src[length_header_size - 1] << 16)  # noqa: W503
                )
            elif literal_length == 63:
                length_header_size += 5
                if length_header_size > src_len:
                    raise CorruptError

                literal_length = (
                    src[length_header_size - 4]
                    | (src[length_header_size - 3] << 8)  # noqa: W503
                    | (src[length_header_size - 2] << 16)  # noqa: W503
                    | (src[length_header_size - 1] << 24)  # noqa: W503
                )

            length = literal_length + 1

            if length <= 0:
                raise BaseSnappyError("Unsupported literal length")
            if length > len(dst) - d or length > src_len - length_header_size:
                raise CorruptError

            dst = list(
                itertools.chain(  # noqa: E203
                    dst[:d],
                    src[length_header_size : length_header_size + length],  # noqa: E203
                    dst[d + length :],  # noqa: E203
                )
            )
            d += length
            length_header_size += length
            continue

        elif elem_type == TAG_COPY1:
            length_header_size += 2
            if length_header_size > src_len:
                raise CorruptError
            length = 4 + ((src[length_header_size - 2] >> 2) & 0x7)
            offset = ((src[length_header_size - 2] & 0xE0) << 3) | src[
                length_header_size - 1
            ]

        elif elem_type == TAG_COPY2:
            length_header_size += 3
            if length_header_size > src_len:
                raise CorruptError
            length = 1 + (src[length_header_size - 3] >> 2)
            offset = src[length_header_size - 2] | (src[length_header_size - 1] << 8)

        elif elem_type == TAG_COPY4:
            raise BaseSnappyError("Unsupported COPY_4 tag")

        end = d + length
        if offset > d or end > len(dst):
            raise CorruptError
        while d < end:
            dst[d] = dst[d - offset]
            d += 1

    if d != block_length:
        raise CorruptError

    return bytes(dst[:d])


MAX_OFFSET = 1 << 15

C240 = 60 << 2
C244 = 61 << 2
C248 = 62 << 2
C252 = 63 << 2
C65536 = 1 << 16
C4294967296 = 1 << 32


@tuple_gen
def emit_literal(lit: bytes) -> Iterable[int]:
    """emit_literal returns a literal chunk."""
    n = len(lit) - 1

    if n < 60:
        yield (uint8(n) << 2) | TAG_LITERAL
    elif n < C240:
        yield C240 | TAG_LITERAL
        yield uint8(n)
    elif n < C244:
        yield C244 | TAG_LITERAL
        yield uint8(n)
        yield uint8(n >> 8)
    elif n < C65536:
        yield C248 | TAG_LITERAL
        yield uint8(n)
        yield uint8(n >> 8)
        yield uint8(n >> 16)
    elif uint64(n) < C4294967296:
        yield C252 | TAG_LITERAL
        yield uint8(n)
        yield uint8(n >> 8)
        yield uint8(n >> 16)
        yield uint8(n >> 24)
    else:
        raise BaseSnappyError("Source buffer is too long")

    yield from lit


C8 = 1 << 3
C64 = 1 << 6
C256 = 1 << 8
C2048 = 1 << 11


@tuple_gen
def emit_copy(offset: int, length: int) -> Iterable[int]:
    """emit_copy writes a copy chunk and returns the number of bytes written."""
    while length > 0:
        x = length - 4
        if 0 <= x and x < C8 and offset < C2048:
            yield ((uint8(offset >> 8) & 0x07) << 5) | (uint8(x) << 2) | TAG_COPY1
            yield uint8(offset)
            break

        x = length
        if x > C64:
            x = C64
        yield (uint8(x - 1) << 2) | TAG_COPY2
        yield uint8(offset)
        yield uint8(offset >> 8)
        length -= x


C24 = 32 - 8
MAX_TABLE_SIZE = 1 << 14


@bytes_gen
def compress(buf: bytes) -> Iterable[int]:
    """compress returns the compressed form of buf."""
    src = tuple(buf)
    src_len = len(src)

    # The block starts with the varint-encoded length of the decompressed bytes.
    yield from (c for c in putuvarint(src_len))

    # Return early if src is short.
    if src_len <= 4:
        if src_len != 0:
            yield from emit_literal(src)
        return

    # Initialize the hash table. Its size ranges from 1<<8 to 1<<14 inclusive.
    shift, table_size = C24, C256
    while table_size < MAX_TABLE_SIZE and table_size < src_len:
        shift -= 1
        table_size *= 2
    table = [0] * MAX_TABLE_SIZE

    # Iterate over the source bytes.
    iter_pos = 0  # The iterator position.
    last_matching_hash_pos = 0  # The last position with the same hash as s.
    literal_start_pos = 0  # The start position of any pending literal bytes.

    while iter_pos + 3 < src_len:
        # Update the hash table.
        b0, b1, b2, b3 = src[iter_pos : iter_pos + 4]  # noqa: E203
        hash_code = (
            uint32(b0) | (uint32(b1) << 8) | (uint32(b2) << 16) | (uint32(b3) << 24)
        )
        hash_bucket = uint32(hash_code * 0x1E35A7BD) >> shift

        # We need to to store values in [-1, inf) in table. To save
        # some initialization time, (re)use the table's zero value
        # and shift the values against this zero: add 1 on writes,
        # subtract 1 on reads.
        last_matching_hash_pos = table[hash_bucket] - 1
        table[hash_bucket] = iter_pos

        if (
            last_matching_hash_pos < 0
            or iter_pos - last_matching_hash_pos >= MAX_OFFSET  # noqa: W503
            or b0 != src[last_matching_hash_pos]  # noqa: W503
            or b1 != src[last_matching_hash_pos + 1]  # noqa: W503
            or b2 != src[last_matching_hash_pos + 2]  # noqa: W503
            or b3 != src[last_matching_hash_pos + 3]  # noqa: W503
        ):
            # If t is invalid or src[s:s+4] differs from src[t:t+4], accumulate a literal byte.
            iter_pos += 1
            continue

        elif literal_start_pos != iter_pos:
            # Otherwise, we have a match. First, emit any pending literal bytes.
            yield from emit_literal(src[literal_start_pos:iter_pos])

        # Extend the match to be as long as possible.
        s0 = iter_pos
        iter_pos = iter_pos + 4
        last_matching_hash_pos = last_matching_hash_pos + 4

        while iter_pos < src_len and src[iter_pos] == src[last_matching_hash_pos]:
            iter_pos += 1
            last_matching_hash_pos += 1

        # Emit the copied bytes.
        yield from emit_copy(iter_pos - last_matching_hash_pos, iter_pos - s0)
        literal_start_pos = iter_pos

    # Emit any final pending literal bytes and return.
    if literal_start_pos != src_len:
        yield from emit_literal(src[literal_start_pos:])
