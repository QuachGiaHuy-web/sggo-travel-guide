# -*- coding: utf-8 -*-
"""
main.py - BACKEND REST API CHO DỰ ÁN SGGO!
Môn học: Công nghệ Phần mềm (COMP1044)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SGGo! Travel Guide API",
    description="API backend phục vụ cẩm nang du lịch và gợi ý lộ trình thông minh Sài Gòn",
    version="1.0.0"
)

# Cấu hình CORS cho phép giao tiếp mượt mà từ frontend
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
