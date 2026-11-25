from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base for domain errors. Services raise these; one handler maps them to HTTP."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class FileTooLargeError(AppError):
    status_code = status.HTTP_413_CONTENT_TOO_LARGE


class UnsupportedFileTypeError(AppError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        # Same {"detail": ...} shape FastAPI uses for its own errors.
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
