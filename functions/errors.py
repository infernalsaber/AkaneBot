class CustomError(Exception):
    """Parent class for all custom errors the bot may encounter"""


class RequestsFailedError(CustomError):
    """
    Exception raised when the API the request is fetched from fails
    """
