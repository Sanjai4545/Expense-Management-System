import sys
import os
import traceback

# Ensure project root is in Python path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from app.main import app
except Exception as e:
    # If the main app fails to import, create a debug app that shows the error
    error_msg = f"{type(e).__name__}: {e}"
    error_trace = traceback.format_exc()

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def show_error(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "startup_error": error_msg,
                "traceback": error_trace,
                "env": {
                    "DATABASE_URL_set": bool(os.getenv("DATABASE_URL")),
                    "SECRET_KEY_set": bool(os.getenv("SECRET_KEY")),
                    "PYTHON_VERSION": sys.version,
                    "CWD": os.getcwd(),
                    "ROOT": ROOT,
                },
            },
        )
