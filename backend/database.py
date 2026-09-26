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

INITIAL_HERITAGE_PLACES = [
    {
        "name": "Chùa Bà Thiên Hậu (Miếu Tuệ Thành)",
        "category": "di_choi",
        "address": "710 Đường Nguyễn Trãi, Phường 11, Quận 5",
        "lat": 10.75338, "lon": 106.65997,
        "open_time": "06:00", "close_time": "17:30",
        "min_price": 0, "max_price": 0, "rating": 4.7, "reviews_count": 3420,
        "image_url": "frontend/images/verified/thien_hau.jpg",
        "tags": "di_1_minh,gia_dinh"
    },
    {
        "name": "Hội Quán Nghĩa An (Chùa Ông)",
        "category": "di_choi",
        "address": "678 Đường Nguyễn Trãi, Phường 11, Quận 5",
        "lat": 10.75389, "lon": 106.66120,
        "open_time": "06:30", "close_time": "18:00",
        "min_price": 0, "max_price": 0, "rating": 4.6, "reviews_count": 1820,
        "image_url": "frontend/images/verified/nghia_an.jpg",
        "tags": "di_1_minh,gia_dinh"
    },
    {
        "name": "Chợ Lớn (Chợ Bình Tây)",
        "category": "di_choi",
        "address": "57A Tháp Mười, Phường 2, Quận 6",
        "lat": 10.74853, "lon": 106.65175,
        "open_time": "06:00", "close_time": "19:00",
        "min_price": 20000, "max_price": 300000, "rating": 4.5, "reviews_count": 5100,
        "image_url": "frontend/images/verified/cho_binh_tay.jpg",
        "tags": "nhom_ban,gia_dinh"
    },
    {
        "name": "Nhà Thờ Cha Tam (Thánh Phanxicô Xaviê)",
        "category": "di_choi",
        "address": "25 Học Lạc, Phường 14, Quận 5",
        "lat": 10.75210, "lon": 106.65580,
        "open_time": "07:00", "close_time": "18:00",
        "min_price": 0, "max_price": 0, "rating": 4.6, "reviews_count": 920,
        "image_url": "frontend/images/verified/nha_tho_cha_tam.jpg",
        "tags": "hen_ho,di_1_minh"
    },
    {
        "name": "Hội Quán Ôn Lăng (Chùa Quan Âm)",
        "category": "di_choi",
        "address": "12 Lão Tử, Phường 11, Quận 5",
        "lat": 10.75520, "lon": 106.66210,
        "open_time": "06:30", "close_time": "17:00",
        "min_price": 0, "max_price": 0, "rating": 4.5, "reviews_count": 640,
        "image_url": "frontend/images/verified/on_lang.jpg",
        "tags": "gia_dinh,di_1_minh"
    }
]

INITIAL_CULINARY_PLACES = [
    {
        "name": "Hủ Tiếu Sa Tế Quảng Ký",
        "category": "an_uong",
        "address": "117 Triệu Quang Phục, Phường 11, Quận 5",
        "lat": 10.75480, "lon": 106.66010,
        "open_time": "16:00", "close_time": "22:00",
        "min_price": 45000, "max_price": 75000, "rating": 4.6, "reviews_count": 520,
        "image_url": "frontend/images/places/place_144.jpg",
        "tags": "nhom_ban,di_1_minh"
    },
    {
        "name": "Sủi Cảo Thiên Thiên (Hà Tôn Quyền)",
        "category": "an_uong",
        "address": "191 Hà Tôn Quyền, Phường 4, Quận 11",
        "lat": 10.75820, "lon": 106.65650,
        "open_time": "13:30", "close_time": "01:00",
        "min_price": 50000, "max_price": 90000, "rating": 4.7, "reviews_count": 2150,
        "image_url": "frontend/images/places/place_145.jpg",
        "tags": "nhom_ban,hen_ho"
    },
    {
        "name": "Cơm Gà Đông Nguyên",
        "category": "an_uong",
        "address": "801 Nguyễn Trãi, Phường 14, Quận 5",
        "lat": 10.75230, "lon": 106.65780,
        "open_time": "09:00", "close_time": "20:30",
        "min_price": 60000, "max_price": 120000, "rating": 4.4, "reviews_count": 1890,
        "image_url": "frontend/images/places/place_147.jpg",
        "tags": "gia_dinh,nhom_ban"
    },
    {
        "name": "Chè Nhà Đèn (Hà Ký)",
        "category": "an_uong",
        "address": "138 Châu Văn Liêm, Phường 11, Quận 5",
        "lat": 10.75260, "lon": 106.66280,
        "open_time": "10:00", "close_time": "22:30",
        "min_price": 25000, "max_price": 50000, "rating": 4.5, "reviews_count": 1420,
        "image_url": "frontend/images/places/place_148.jpg",
        "tags": "hen_ho,nhom_ban"
    },
    {
        "name": "Dimsum Tiến Phát",
        "category": "an_uong",
        "address": "18 Ký Hòa, Phường 11, Quận 5",
        "lat": 10.75410, "lon": 106.66150,
        "open_time": "06:00", "close_time": "12:30",
        "min_price": 50000, "max_price": 150000, "rating": 4.6, "reviews_count": 2300,
        "image_url": "frontend/images/places/place_150.jpg",
        "tags": "gia_dinh,nhom_ban"
    }
]

def seed_users_if_needed(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
        INSERT INTO users (username, password, full_name, role)
        VALUES 
            ('admin', 'admin123', 'Quản Trị Viên SGGo', 'admin'),
            ('user1', '123456', 'Khách Du Lịch Mẫu', 'user')
        """)
        conn.commit()

def seed_places_if_needed(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM places")
    if cursor.fetchone()["count"] == 0:
        all_seeds = INITIAL_HERITAGE_PLACES + INITIAL_CULINARY_PLACES
        for p in all_seeds:
            cursor.execute("""
            INSERT INTO places (name, category, address, lat, lon, open_time, close_time, min_price, max_price, rating, reviews_count, image_url, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["name"], p["category"], p["address"], p["lat"], p["lon"],
                p["open_time"], p["close_time"], p["min_price"], p["max_price"],
                p["rating"], p["reviews_count"], p.get("image_url"), p.get("tags")
            ))
        conn.commit()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
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

    seed_users_if_needed(conn)
    seed_places_if_needed(conn)
    conn.close()

def get_all_places(category=None, min_rating=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM places WHERE 1=1"
    params = []

    if category and category != "all":
        query += " AND category = ?"
        params.append(category)

    if min_rating:
        query += " AND rating >= ?"
        params.append(float(min_rating))

    query += " ORDER BY rating DESC"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    places = [dict(row) for row in rows]
    conn.close()
    return places

def get_place_by_id(place_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM places WHERE id = ?", (int(place_id),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
