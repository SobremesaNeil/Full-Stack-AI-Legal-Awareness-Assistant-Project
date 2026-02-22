import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from models import Base
import os
from dotenv import load_dotenv

load_dotenv()

async def init_db():
    # 获取数据库 URL
    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:
        raise ValueError("DATABASE_URL environment variable must be set")

    # 创建异步数据库引擎
    engine = create_async_engine(database_url, echo=False)

    try:
        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("数据库表创建成功！")
    except Exception as e:
        print(f"创建数据库表时出错: {str(e)}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db()) 