import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.main import app
except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()

    @app.get("/{path:path}")
    @app.post("/{path:path}")
    def error_handler(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "type": type(e).__name__,
                "database_url_set": bool(os.getenv("DATABASE_URL")),
                "secret_key_set": bool(os.getenv("SECRET_KEY")),
            }
        )
