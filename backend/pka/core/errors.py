"""One JSON shape for every failure. Internal detail goes to the log, never the response."""

import logging
from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

log = logging.getLogger(__name__)


def install(app: FastAPI) -> None:
    """Send every failure through the handlers below. Starlette's HTTPException also covers
    the 404s and 405s raised by routing itself, which never reach FastAPI's subclass."""
    app.add_exception_handler(HTTPException, _known)
    app.add_exception_handler(RequestValidationError, _invalid)
    app.add_exception_handler(Exception, _unexpected)


def _reply(code: int, message: str, headers: Mapping[str, str] | None = None) -> JSONResponse:
    # The code is the status phrase, so a new status needs no new entry anywhere.
    name = HTTPStatus(code).phrase.lower().replace(" ", "_")
    return JSONResponse({"error": {"code": name, "message": message}}, code, headers)


def _known(_: Request, exc: Exception) -> JSONResponse:
    """A status a route chose, with a message written for the caller."""
    assert isinstance(exc, HTTPException)
    return _reply(exc.status_code, str(exc.detail), exc.headers)


def _invalid(_: Request, exc: Exception) -> JSONResponse:
    """Validation failed. The default body echoes the submitted values; this one does not."""
    return _reply(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid request")


def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    """A bug. The caller learns only that it happened; the traceback stays in the log."""
    log.error("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return _reply(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")
