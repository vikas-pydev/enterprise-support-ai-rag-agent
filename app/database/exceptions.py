class DatabaseError(Exception):
    """Base exception for sanitized application database errors.

    Ensures internal database details, passwords, or connection strings
    are never leaked to callers or logging outputs.
    """
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error
