from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app import models
import logging
from app.routers import (auth, employees,departments, attendance, dashboard, leaves)
from fastapi import Request


app = FastAPI( title="Employee Management System(EMS)", description= "A smart API for workforce management, employee records, leave tracking, and attendance.", version="1.0.0")
logger = logging.getLogger(__name__)

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:5173"],  allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {"field": ".".join(str(part) for part in error["loc"]),"message": error["msg"],}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"message": "Please check the submitted information.", "errors": errors,},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    message = ( exc.detail if isinstance(exc.detail, str) else "The request could not be completed." )
    return JSONResponse( status_code=exc.status_code, content={"message": message, "errors": []}, headers=exc.headers, )


@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error( "Unhandled API error", exc_info=(type(exc), exc, exc.__traceback__), )
    return JSONResponse(
        status_code=500,
        content={ "message": "An unexpected error occurred. Please try again later.", "errors": []},
    )


app.include_router( auth.router, prefix="/auth", tags=["Authentication"])

app.include_router( employees.router, prefix="/employees", tags=["Employees"])

app.include_router( departments.router, prefix="/departments", tags=["Department"])

app.include_router( attendance.router, prefix="/attendance", tags=["Attendance"])

app.include_router( leaves.router, prefix="/leaves", tags=["Leaves"])

app.include_router( dashboard.router, prefix="/dashboard", tags=["Dashboard"])

