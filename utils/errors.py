class CustomError(Exception):
    """Parent class for all custom errors the bot may encounter"""


class RequestsFailedError(CustomError):
    """
    Exception raised when the API the request is fetched from fails
    """


class TransportError(RequestsFailedError):
    """Raised on network error, non-OK HTTP status, or retries exhausted."""


class AniListError(RequestsFailedError):
    """Raised when AniList GraphQL returns a hard failure (non-retryable or retries exhausted)."""
