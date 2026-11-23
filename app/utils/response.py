
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(
    message: str,
    data: Any = None,
    status_code: int = 200,
    *,
    meta: dict[str, Any] | None = None,
):
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "success": True,
            "message": message,
            "status_code": status_code,
            "data": data if data is not None else {},
            **({"meta": meta} if meta is not None else {}),
        })
    )


def error_response(
    message: str,
    status_code: int = 400,
    data: Any = None
):
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "success": False,
            "message": message,
            "status_code": status_code,
            "data": data if data is not None else {}
        })
    )
