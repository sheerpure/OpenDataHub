# from fastapi import FastAPI

# app = FastAPI(title="OpenDataHub - Mini Depositar")

# @app.get("/")
# def read_root():
#     return {"message": "Hello from OpenDataHub! 🚀 這是我的研究資料平台 demo"}

# @app.get("/docs")
# def docs():
#     return {"redirect": "去 http://127.0.0.1:8000/docs 看自動 API 文件"}

# @app.get("/hello/{name}")
# def say_hello(name: str):
#     return {"message": f"嗨，{name}！歡迎來到 OpenDataHub 🎉"}

from fastapi import FastAPI, Depends, Query, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi.security import OAuth2PasswordRequestForm
import math

# 引入自定義模組
from database import get_db
import models
import schemas
import auth
from search import full_text_search
from search import index_dataset
from auth import get_current_user

# 設定模板
templates = Jinja2Templates(directory="templates")

# 初始化應用程式
app = FastAPI(
    title="OpenDataHub",
    description="Mini research data repository platform inspired by depositar.",
    version="0.2.0"
)

# 網頁路由 (Frontend Shell)

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
def home(request: Request):
    """回傳首頁 HTML，資料將由前端 JavaScript 透過 API 非同步抓取"""
    return templates.TemplateResponse("index.html", {"request": request})


#  身份驗證 API (Auth)

@app.post("/api/v1/auth/register", response_model=schemas.UserSchema, tags=["Auth"])
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """使用者註冊：檢查重複並加密儲存密碼"""
    db_user = db.query(models.User).filter(
        or_(models.User.username == user_in.username, models.User.email == user_in.email)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="帳號或 Email 已被註冊")
    
    new_user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=auth.hash_password(user_in.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/v1/auth/login", tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """使用者登入：驗證成功後簽發 JWT Token"""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/users/me", tags=["Auth"], response_model=schemas.UserSchema)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """取得目前登入的使用者資訊 (受保護路徑，須帶 Token)"""
    return current_user


# 資料集 API (Datasets) 

@app.get("/api/v1/datasets", tags=["Datasets"], response_model=schemas.DatasetResponse)
def get_datasets(q: str = Query(None), page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    """取得資料集列表：支援全文搜尋 (ES) 與分頁查詢 (PG)"""
    size = 10
    if q:
        # 執行 Elasticsearch 搜尋
        search_data = full_text_search(q, page=page, size=size)
        formatted_data = [
            {
                "title": hit['_source'].get("title"),
                "description": hit['_source'].get("description"),
                "author": hit['_source'].get("author"),
                "created_at": str(hit['_source'].get("created_at"))[:10]
            }
            for hit in search_data["hits"]
        ]
        return {
            "status": "success",
            "data": formatted_data,
            "pagination": {
                "current_page": page,
                "total_items": search_data["total"],
                "total_pages": math.ceil(search_data["total"] / size)
            }
        }
    else:
        # 從 PostgreSQL 抓取最新資料
        db_query = db.query(models.Dataset)
        total_items = db_query.count()
        db_data = db_query.offset((page-1)*size).limit(size).all()
        
        formatted_db_data = [
            {
                "title": ds.title,
                "description": ds.description,
                "author": ds.author,
                "created_at": ds.created_at.strftime("%Y-%m-%d") if ds.created_at else None
            }
            for ds in db_data
        ]
        return {
            "status": "success",
            "data": formatted_db_data,
            "pagination": {
                "current_page": page,
                "total_items": total_items,
                "total_pages": math.ceil(total_items / size)
            }
        }

@app.get("/api/v1/datasets/{dataset_id}", tags=["Datasets"], response_model=schemas.DatasetSchema)
def get_dataset_detail(dataset_id: int, db: Session = Depends(get_db)):
    """取得特定資料集的詳細資訊"""
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="找不到該資料集")
    return dataset



from search import index_dataset # 確保你有這個匯入

@app.post("/api/v1/datasets", tags=["Datasets"], status_code=201)
def upload_dataset(
    dataset_in: schemas.DatasetSchema, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    [受保護路徑] 建立新的資料集並同步至 Elasticsearch
    """
    # 1. 存入 PostgreSQL
    new_data = models.Dataset(
        title=dataset_in.title,
        description=dataset_in.description,
        author=dataset_in.author,
        # 這裡可以紀錄是誰上傳的：owner_id=current_user.id
    )
    db.add(new_data)
    db.commit()
    db.refresh(new_data)

    # 2. 同步到 Elasticsearch (讓搜尋立刻找得到)
    try:
        index_dataset(
            new_data.id, 
            new_data.title, 
            new_data.description, 
            new_data.author, 
            str(new_data.created_at)[:10]
        )
    except Exception as e:
        print(f"ES 同步失敗: {e}")

    return {"status": "success", "id": new_data.id}