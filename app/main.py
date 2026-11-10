import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.database import engine, Base, init_tables
from app.errors import ApiError
from fastapi.staticfiles import StaticFiles
from app.routers import auth, groups, expenses, settlements
import app.models  # Register models

logger = logging.getLogger("halfway")

# Pre-initialize tables on import if possible
try:
    init_tables()
except Exception as e:
    logger.warning("Startup table creation skipped: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_tables()
    except Exception as e:
        logger.warning("Lifespan table creation skipped: %s", e)
    yield


app = FastAPI(title="Halfway", lifespan=lifespan)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields = {}
    for err in exc.errors():
        loc = err.get("loc", [])
        field_name = str(loc[-1]) if loc else "value"
        if field_name == "body" and len(loc) > 1:
            field_name = str(loc[-2])
        msg = err.get("msg", "Invalid value")
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        fields[field_name] = msg

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Please fix the highlighted fields.",
                "fields": fields,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
    }
    code = code_map.get(exc.status_code, "error")
    msg = exc.detail if isinstance(exc.detail, str) else "An error occurred"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": msg,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "server_error",
                "message": f"Server error: {type(exc).__name__}: {str(exc)}",
            }
        },
    )


# Health check endpoints
@app.get("/health")
@app.get("/api/health")
def health():
    """Check app and database health."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": f"{type(e).__name__}: {str(e)}"}


# Register API routers with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(groups.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(settlements.router, prefix="/api")

# Also register without /api prefix in case URL rewrite strips /api
app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(expenses.router)
app.include_router(settlements.router)


# Mount static frontend files if directory exists locally
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
