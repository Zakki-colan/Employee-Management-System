
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import models
from app.routers import (
    auth,
    employees,
    departments,
    attendance,
    dashboard,
    leaves,
    employee_document,
    employee_promotion,
    holidays
)
from app.utils.response import error_response


logger = logging.getLogger(__name__)

app = FastAPI(
    title="Employee Management System(EMS)",
    description=(
        "A smart API for workforce management, employee records, "
        "leave tracking, attendance, and promotions."
    ),
    version="1.0.0",
    docs_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/docs", include_in_schema=False)
async def swagger_docs(request: Request):
    root_path = request.scope.get("root_path", "").rstrip("/")
    docs = get_swagger_ui_html(
        openapi_url=f"{root_path}{app.openapi_url}",
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=f"{root_path}/docs/oauth2-redirect",
    )
    # Keep Swagger's enum and default for the status control while hiding its duplicate labels.
    styles = """
    <style>
      #operations-Leaves-get_leave_history_leaves_history_get :is(
        .parameters thead,
        tr[data-param-name="status"][data-param-in="query"] .parameters-col_name,
        tr[data-param-name="status"][data-param-in="query"] .parameter__enum,
        tr[data-param-name="status"][data-param-in="query"] .parameter__default,
        tr[data-param-name="status"][data-param-in="query"] select option[value=""]
      ) {
        display: none;
      }
    </style>
    """
    return HTMLResponse(bytes(docs.body).decode().replace("</head>", f"{styles}</head>", 1))


@app.get("/docs/oauth2-redirect", include_in_schema=False)
async def swagger_oauth2_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    message = (
        exc.detail
        if isinstance(exc.detail, str)
        else "The request could not be completed."
    )

    return error_response(
        message=message,
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]

    return error_response(
        message="Please check the submitted information.",
        status_code=400,
        data={"errors": errors},
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.error(
        "Unhandled API error",
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return error_response(
        message="An unexpected error occurred. Please try again later.",
        status_code=500,
    )


app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(employees.router, prefix="/employees", tags=["Employees"])
app.include_router(departments.router, prefix="/departments", tags=["Department"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
app.include_router( employee_promotion.router, prefix="/employees", tags=["Employee Promotions"],)
app.include_router(leaves.router, prefix="/leaves", tags=["Leaves"])
app.include_router( employee_document.router, prefix="/document", tags=["Employee Documents"])
app.include_router(holidays.router, prefix="/holidays", tags=["Holiday Management"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])