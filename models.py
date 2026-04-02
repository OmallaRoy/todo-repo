from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import os

Base = declarative_base()


class Todo(Base):
    """
    Represents a single todo item belonging to a user.

    Schema:
        id        - Auto-incrementing primary key (INTEGER)
        user_id   - Firebase UID of the owning user (VARCHAR 128)
        email     - Email of the owning user, stored for display (VARCHAR 255)
        title     - The task text (TEXT)
        created   - Timestamp when the todo was created (DATETIME, UTC)
    """
    __tablename__ = 'todos'

    id      = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, index=True)
    email   = Column(String(255), nullable=False)
    title   = Column(Text, nullable=False)
    created = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Todo id={self.id} user={self.email!r} title={self.title!r}>"


def get_engine():
    """Create SQLAlchemy engine from Railway DATABASE_URL env var."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    # Railway Postgres URLs start with postgres://, SQLAlchemy needs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return create_engine(database_url, pool_pre_ping=True)


def get_session_factory(engine):
    return sessionmaker(bind=engine)


def init_db(engine):
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(engine)