from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

# When USE_MOCK=true, fall back to a local SQLite database so the project can
# run without a PostgreSQL instance.  The SQLite file is created automatically.
_default_db_url = (
    "sqlite+aiosqlite:///./mock.db"
    if USE_MOCK
    else "postgresql+asyncpg://postgres:postgres@localhost:5432/chatbot"
)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", _default_db_url)

# SQLite requires check_same_thread=False when used with aiosqlite: the library
# runs SQLite in a background thread per connection and handles its own
# serialisation, so disabling the same-thread check is both necessary and safe.
_connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

# 使用 create_async_engine
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True, connect_args=_connect_args)

# 使用 AsyncSession
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

# 异步的依赖注入函数
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()