"""SQLAlchemy sync sessions; PostgreSQL for deployments, SQLite for local development."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings

class Base(DeclarativeBase):
    pass

def make_engine(url: str):
    args = {'check_same_thread': False, 'timeout': 30} if url.startswith('sqlite:') else {}
    eng = create_engine(url, future=True, pool_pre_ping=True, connect_args=args)
    if url.startswith('sqlite:'):
        @event.listens_for(eng, 'connect')
        def set_sqlite_pragmas(dbapi_connection, _):
            c = dbapi_connection.cursor()
            c.execute('PRAGMA foreign_keys=ON')
            c.execute('PRAGMA busy_timeout=30000')
            c.close()
    return eng

engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

def init_db():
    # A real deployment must apply versioned migrations before starting.
    from app.domain import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

def get_db():
    with SessionLocal() as session:
        yield session
