class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: int | str) -> None:
        super().__init__(f"{resource} {identifier} not found", status_code=404)
