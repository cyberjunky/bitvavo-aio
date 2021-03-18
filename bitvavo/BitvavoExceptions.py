"""Error definitions."""


class BitvavoException(Exception):
    """Raised when API error occurs."""

    def __init__(self, status_code, message):

        self.status_code = status_code
        self.message = message

    def __str__(self):  # pragma: no cover
        return "Error(code=%s): %s" % (self.status_code, self.message)
