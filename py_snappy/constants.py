TAG_LITERAL = 0x00
TAG_COPY1 = 0x01
TAG_COPY2 = 0x02
TAG_COPY4 = 0x03

# https://code.google.com/p/snappy/source/browse/trunk/framing_format.txt says
# that "the uncompressed data in a chunk must be no longer than 65536 bytes".
# TODO: enforce this.
MAX_UNCOMPRESSED_CHUNK_LEN = 65536
