STALE_DATA_ERROR_MESSAGE = (
    "Mint sync apparently incomplete after timeout.  Data retrieved may not be current."
)

# define Python user-defined exceptions
class Error(Exception):
    """Base class for other exceptions"""

    pass


class StaleDataException(Error):
    """Exception class for when Mint cannot refresh account data in a sufficient timeframe."""

    pass
