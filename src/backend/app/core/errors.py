from fastapi import Request
from fastapi.exceptions import RequestValidationError
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


class ResourceNotFound(ApiError):
    def __init__(self, message: str = "The requested resource was not found.") -> None:
        super().__init__(404, "not_found", message)


class Conflict(ApiError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(409, code, message)


class InvalidRequest(ApiError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(400, code, message)


async def api_error_handler(_: Request, error: ApiError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Session"} if error.status_code == 401 else None
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message}},
        headers=headers,
    )


async def request_validation_error_handler(
    _: Request, error: RequestValidationError
) -> JSONResponse:
    messages = [str(item.get("msg", "Invalid value.")) for item in error.errors()[:5]]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": " ".join(messages) or "The request is invalid.",
            }
        },
    )
