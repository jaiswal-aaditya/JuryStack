from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class AuthenticationRequired(ApiError):
    def __init__(self, message: str = "Authentication is required.") -> None:
        super().__init__(401, "authentication_required", message)


class PermissionDenied(ApiError):
    def __init__(
        self, message: str = "You do not have permission for this action."
    ) -> None:
        super().__init__(403, "permission_denied", message)


async def api_error_handler(_: Request, error: ApiError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Session"} if error.status_code == 401 else None
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message}},
        headers=headers,
    )
