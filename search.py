# search.py
from elasticsearch import Elasticsearch

# 透過 URL 的 http/https 來判斷是否加密
# 關閉 verify_certs 以確保開發環境連線順暢
es = Elasticsearch(
    "http://localhost:9200",
    verify_certs=False,
    request_timeout=30,
    headers={"Accept": "application/vnd.elasticsearch+json; compatible-with=8"}
)

INDEX_NAME = "opendatahub_datasets"

def create_index():
    """檢查索引是否存在並建立"""
    try:
        # 使用 exists 檢查索引
        if not es.indices.exists(index=INDEX_NAME):
            es.indices.create(index=INDEX_NAME, body={
                "mappings": {
                    "properties": {
                        "title": {"type": "text", "analyzer": "standard"},
                        "description": {"type": "text", "analyzer": "standard"},
                        "author": {"type": "keyword"},
                        "created_at": {"type": "date"}
                    }
                }
            })
            print(f"✅ 成功建立索引: {INDEX_NAME}")
    except Exception as e:
        print(f"⚠️ 處理索引時發生非預期錯誤: {e}")

def index_dataset(dataset_id, title, description, author, created_at):
    """將單筆資料寫入 ES"""
    doc = {
        "title": title,
        "description": description,
        "author": author,
        "created_at": created_at
    }
    es.index(index=INDEX_NAME, id=dataset_id, document=doc)

def full_text_search(query_str, page=1, size=10):
    """支援分頁的全文檢索"""
    start = (page - 1) * size # 計算跳過的筆數
    
    query_body = {
        "query": {
            "multi_match": {
                "query": query_str,
                "fields": ["title^3", "description"]
            }
        },
        "from": start,  # 跳過前 N 筆
        "size": size,    # 只抓 N 筆
        "highlight": {
            "pre_tags": ["<mark class='bg-warning'>"], # 使用 Bootstrap 的黃色背景標籤
            "post_tags": ["</mark>"],
            "fields": {
                "title": {},
                "description": {}
            }
        }
    }
    response = es.search(index=INDEX_NAME, body=query_body)
    
    # 回傳結果與總筆數 (為了計算總頁數)
    return {
        "hits": response['hits']['hits'],
        "total": response['hits']['total']['value']
    }