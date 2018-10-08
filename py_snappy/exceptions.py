class BaseSnappyError(Exception):
    """
    Base error class for snappy module.
    """


class CorruptError(BaseSnappyError):
    """
    Corrupt input.
    """


class TooLargeError(BaseSnappyError):
    """
    Decoded block is too large.
    """
