import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/test.db'))
DATABASE_URL = fr"sqlite+aiosqlite:///{db_path}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def create_db():
    import sqlite3

    sqlite3.connect(db_path).close()


create_db()