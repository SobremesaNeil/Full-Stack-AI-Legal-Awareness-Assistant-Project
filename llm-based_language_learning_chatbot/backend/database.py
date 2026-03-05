from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# 注意这里增加了 +asyncpg (PostgreSQL) 或 +aiosqlite (SQLite)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./chatbot.db"
)

# SQLite 需要额外配置 check_same_thread=False
db_connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

# 使用 create_async_engine
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True, connect_args=db_connect_args)

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