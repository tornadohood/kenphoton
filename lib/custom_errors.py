"""Common location for custom exceptions in photon."""


class CustomException(Exception):
    """Base class for all non-standard exceptions."""
    pass


class FormatError(CustomException):
    """Generic Exception for Formatting errors."""
    pass


class HardwareComponentError(CustomException):
    """Generic Exception for errors with Hardware Components."""
    pass


class HardwareGroupError(CustomException):
    """Generic Exception for errors with Hardware Groups."""
    pass


class HardwareCompatibilityError(CustomException):
    """Generic Exception for errors with Hardware Compatibility."""
    pass


class InsufficientDataError(CustomException):
    """Generic Exception for when we don't have enough data/information to continue."""
    pass


class LogParserError(CustomException):
    """Generic Exception for any known error that is not safe to ignore."""
    pass


class LogParserSkippableError(LogParserError):
    """Generic Exception for any known error that is safe to ignore."""
    pass


class ParsingError(CustomException):
    """Raised when a parser cannot fetch information."""
    pass


class SSHError(CustomException):
    """Errors while connecting to and working with a remote server."""
    pass


# Intentional override of build-in for Python2/3 compatibility
# pylint: disable=redefined-builtin
class TimeoutError(CustomException):
    """Error related to a function taking longer than expected to run."""
    pass
