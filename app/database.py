import logging
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from app.config import DATABASE_URL

logger = logging.getLogger("halfway")

connect_args = {}
engine_kwargs = {}

if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
elif "postgresql" in DATABASE_URL:
    # On serverless (Vercel) connecting to Neon's PgBouncer pooler,
    # NullPool is required to prevent frozen/broken connection reuse
    engine_kwargs["poolclass"] = NullPool
    if "sslmode" not in DATABASE_URL:
        connect_args["sslmode"] = "require"

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

if "sqlite" in DATABASE_URL:
    @event.listens_for(Engine, "connect")
    def _fk_pragma(dbapi_conn, _):
        """Enable foreign keys for SQLite on every connection."""
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

_tables_initialized = False

def init_tables():
    """Ensure database tables exist on Neon PostgreSQL."""
    global _tables_initialized
    if not _tables_initialized:
        try:
            import app.models  # Register all models with Base.metadata
            Base.metadata.create_all(bind=engine)
            _tables_initialized = True
            logger.info("Database tables initialized successfully.")
        except Exception as e:
            logger.error("Failed to create tables: %s", e)
            raise e

def get_db():
    init_tables()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
