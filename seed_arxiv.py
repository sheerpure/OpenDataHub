import pandas as pd
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Dataset, User
from search import index_dataset, create_index
import json

Base.metadata.create_all(bind=engine)

def seed_from_arxiv(file_path, limit=1000):
    db = SessionLocal()
    create_index()
    
    
    admin = db.query(User).filter(User.username == "arxiv_admin").first()
    if not admin:
        admin = User(username="arxiv_admin", email="admin@arxiv.org", hashed_password="secure_password")
        db.add(admin)
        db.commit()
        db.refresh(admin)
    # ---------------------------------------

    print(f"正在讀取 {file_path} ...")
    count = 0
    with open(file_path, 'r') as f:
        for line in f:
            if count >= limit:
                break
            
            data = json.loads(line)
            
            new_dataset = Dataset(
                title=data.get('title', 'No Title'),
                description=data.get('abstract', 'No Description'),
                author=data.get('authors', 'Unknown'),
                license="CC-BY-4.0",
                owner_id=admin.id 
            )
            db.add(new_dataset)
            db.flush() # 取得 ID 用於 ES 同步

            # 同步到 Elasticsearch
            try:
                index_dataset(
                    dataset_id=new_dataset.id, 
                    title=new_dataset.title, 
                    description=new_dataset.description,
                    author=new_dataset.author,
                    created_at=new_dataset.created_at
                )
            except Exception as e:
                # 如果 ES 同步失敗，印出但不中斷 DB 匯入
                print(f"ES 同步失敗筆數 {count}: {e}")

            count += 1
            if count % 100 == 0:
                db.commit()
                print(f"已匯入並同步至 ES: {count} 筆...")

    db.commit()
    db.close()
    print(f"✅ 成功完成 {count} 筆資料同步！")

if __name__ == "__main__":
    seed_from_arxiv(r"C:\Users\user\Desktop\opendatahub\archive\arxiv-metadata-oai-snapshot.json")