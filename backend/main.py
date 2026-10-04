import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="SGGo! Backend API")

# Cấu hình CORS để Frontend gọi được API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nạp dữ liệu địa điểm thật
DATA_FILE = os.path.join(os.path.dirname(__file__), "enriched_places.json")

def load_places():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

PLACES_DB = load_places()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SGGo! Backend is running with real OSM & Google Maps data"}

@app.get("/api/places")
def get_places(category: Optional[str] = None):
    """Lấy danh sách địa điểm theo danh mục (an_uong, di_choi, homestay, workshop)"""
    if category and category != "all":
        filtered = [p for p in PLACES_DB if p.get("category") == category]
        return filtered
    return PLACES_DB

@app.get("/api/stats")
def get_stats():
    """API thống kê số liệu phục vụ báo cáo tiến độ"""
    total = len(PLACES_DB)
    verified = sum(1 for p in PLACES_DB if p.get("is_verified"))
    return {
        "total_places": total,
        "verified_places": verified,
        "unverified_places": total - verified,
        "categories": {
            "an_uong": sum(1 for p in PLACES_DB if p.get("category") == "an_uong"),
            "di_choi": sum(1 for p in PLACES_DB if p.get("category") == "di_choi"),
            "homestay": sum(1 for p in PLACES_DB if p.get("category") == "homestay"),
            "workshop": sum(1 for p in PLACES_DB if p.get("category") == "workshop"),
        }
    }