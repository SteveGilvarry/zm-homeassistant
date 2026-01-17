"""Exceptions for the ZoneMinder integration."""


class ZoneMinerError(Exception):
    """Base exception for ZoneMinder integration."""


class ZMConnectionError(ZoneMinerError):
    """Exception raised when connection to ZoneMinder fails."""


class ZMAuthenticationError(ZoneMinerError):
    """Exception raised when authentication with ZoneMinder fails."""


class ZMApiError(ZoneMinerError):
    """Exception raised when ZoneMinder API returns an error."""
