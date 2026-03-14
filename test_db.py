from sqlalchemy import create_engine, text  
from config import settings

Base.metadata.drop_all(bind=engine)
engine = create_engine(settings.DATABASE_URL)

try:
    with engine.connect() as connection:
        print("資料庫連線成功！")
        # 使用 text() 包裹 SQL 字串
        result = connection.execute(text("SELECT version();"))
        print("PostgreSQL 版本：", result.fetchone()[0])
except Exception as e:
    print("連線失敗：", e)

