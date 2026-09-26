# -*- coding: utf-8 -*-
"""
main.py - BACKEND REST API CHO DỰ ÁN SGGO!
Môn học: Công nghệ Phần mềm (COMP1044)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from backend.database import init_db, get_all_places, get_place_by_id

# Khởi tạo CSDL SQLite khi server bật
init_db()

app = FastAPI(
    title="SGGo! Travel Guide API",
    description="API backend phục vụ cẩm nang du lịch và gợi ý lộ trình thông minh Sài Gòn",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "Chào mừng đến với SGGo! Travel Guide API",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "sggo-backend"}

@app.get("/api/places")
def fetch_places(
    category: Optional[str] = Query(None, description="Lọc theo 'an_uong', 'di_choi' hoặc 'all'"),
    min_rating: Optional[float] = Query(None, description="Điểm đánh giá tối thiểu (VD: 4.5)")
):
    """Trả về danh sách địa điểm theo bộ lọc"""
    places = get_all_places(category=category, min_rating=min_rating)
    return {
        "count": len(places),
        "places": places
    }

@app.get("/api/places/{place_id}")
def fetch_place_detail(place_id: int):
    """Trả về thông tin chi tiết một địa điểm theo ID"""
    place = get_place_by_id(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm yêu cầu")
    return place
