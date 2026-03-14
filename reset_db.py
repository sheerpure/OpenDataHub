
from database import engine, Base
import models

def reset_database():
    print("正在清空舊有資料表...")
    Base.metadata.drop_all(bind=engine)
    print("正在重新建立資料表結構...")
    Base.metadata.create_all(bind=engine)
    print("✅ 資料庫已成功重置！")

if __name__ == "__main__":
    reset_database()