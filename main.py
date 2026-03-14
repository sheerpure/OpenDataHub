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

from fastapi import FastAPI, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db, engine
import models
from search import full_text_search
import math

# 設定模板目錄
templates = Jinja2Templates(directory="templates")

app = FastAPI(title="OpenDataHub")

# 修改根目錄路由，讓它回傳 HTML
@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = Query(None), page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    size = 10  # 每頁顯示 10 筆
    results = []
    total_pages = 0

    if q:
        # 改用支援分頁的 ES 搜尋
        search_data = full_text_search(q, page=page, size=size)
        es_hits = search_data["hits"]
        total_count = search_data["total"]
        total_pages = math.ceil(total_count / size)

        for hit in es_hits:
            source = hit['_source']
            highlight = hit.get('highlight', {})
            
            title = highlight.get('title', [source.get('title')])[0]
            description = highlight.get('description', [source.get('description')])[0]
            raw_date = source.get("created_at", "")
            results.append({
                "title": title,
                "author": source.get("author"),
                "description": description,
                "created_at": raw_date[:10] if raw_date else "未知日期"
            })
    else:
        # DB 搜尋支援分頁 (SQL offset/limit)
        total_count = db.query(models.Dataset).count()
        total_pages = math.ceil(total_count / size)
        db_data = db.query(models.Dataset).offset((page-1)*size).limit(size).all()
        for ds in db_data:
            results.append({
                "title": ds.title, "author": ds.author, 
                "description": ds.description, "created_at": ds.created_at.strftime('%Y-%m-%d')
            })

    return templates.TemplateResponse("index.html", {
        "request": request,
        "results": results,
        "q": q,
        "page": page,
        "total_pages": total_pages
    })