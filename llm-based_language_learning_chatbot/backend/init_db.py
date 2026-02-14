from sqlalchemy import create_engine
from models import Base
import os
from dotenv import load_dotenv

load_dotenv()

def init_db():
    # 获取数据库 URL
    database_url = os.getenv(
        "DATABASE_URL"
    )
    
    # 创建数据库引擎
    engine = create_engine(database_url)
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("数据库表创建成功！")
    except Exception as e:
        print(f"创建数据库表时出错: {str(e)}")
        raise

if __name__ == "__main__":
    init_db() 