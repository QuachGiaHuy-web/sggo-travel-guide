# -*- coding: utf-8 -*-
"""
database.py - QUẢN LÝ CƠ SỞ DỮ LIỆU SQLITE CHO DỰ ÁN SGGO!
Môn học: Công nghệ Phần mềm (COMP1044)
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "sggo.db")

def get_connection():
    """Tạo kết nối tới file SQLite, trả về sqlite3.Row để truy xuất dữ liệu theo tên cột"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Khởi tạo cấu trúc các bảng: users, places, favorites"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. BẢNG USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user', -- 'admin' hoặc 'user'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. BẢNG PLACES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,               -- 'an_uong' hoặc 'di_choi'
        address TEXT NOT NULL,
        district TEXT NOT NULL DEFAULT 'Quận 5',
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        open_time TEXT NOT NULL DEFAULT '08:00',
        close_time TEXT NOT NULL DEFAULT '22:00',
        min_price INTEGER NOT NULL DEFAULT 30000,
        max_price INTEGER NOT NULL DEFAULT 100000,
        rating REAL NOT NULL DEFAULT 4.5,
        reviews_count INTEGER NOT NULL DEFAULT 100,
        image_url TEXT,
        tags TEXT DEFAULT 'nhom_ban'
    );
    """)

    # 3. BẢNG FAVORITES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        place_id INTEGER NOT NULL,
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
        UNIQUE(user_id, place_id)
    );
    """)

    conn.commit()
    conn.close()
