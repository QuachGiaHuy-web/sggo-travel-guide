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

import hashlib

def hash_password(password: str) -> str:
    """Băm mật khẩu bằng thuật toán SHA-256 kèm salt"""
    salt = "sggo_travel_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu nhập vào khớp với chuỗi băm lưu trữ"""
    return hash_password(plain_password) == hashed_password

def register_user(username, password, full_name):
    """Đăng ký tài khoản người dùng mới"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username.strip(),))
    if cursor.fetchone():
        conn.close()
        return None, "Tên đăng nhập đã tồn tại"

    hashed = hash_password(password)
    cursor.execute("""
    INSERT INTO users (username, password, full_name, role)
    VALUES (?, ?, ?, 'user')
    """, (username.strip(), hashed, full_name.strip()))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": user_id, "username": username, "full_name": full_name, "role": "user"}, None

def authenticate_user(username, password):
    """Xác thực tài khoản và trả về thông tin người dùng"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None, "Tài khoản không tồn tại"

    user = dict(row)
    # Hỗ trợ cả mật khẩu băm và mật khẩu cũ của seed
    if user["password"] == password or verify_password(password, user["password"]):
        return {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"]
        }, None

    return None, "Mật khẩu không chính xác"

def add_place(place_dict):
    """Thêm địa điểm mới vào CSDL với dữ liệu hợp lệ"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO places (
        name, category, address, district, lat, lon, open_time, close_time,
        min_price, max_price, rating, reviews_count, image_url, tags
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        place_dict["name"], place_dict["category"], place_dict["address"],
        place_dict.get("district", "Quận 5"),
        float(place_dict["lat"]), float(place_dict["lon"]),
        place_dict.get("open_time", "08:00"), place_dict.get("close_time", "22:00"),
        int(place_dict.get("min_price", 30000)), int(place_dict.get("max_price", 100000)),
        float(place_dict.get("rating", 4.5)), int(place_dict.get("reviews_count", 50)),
        place_dict.get("image_url", ""), place_dict.get("tags", "nhom_ban")
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_place(place_id: int, p: dict):
    """Cập nhật thông tin địa điểm theo ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE places SET
        name = ?, category = ?, address = ?, lat = ?, lon = ?,
        open_time = ?, close_time = ?, min_price = ?, max_price = ?,
        rating = ?, image_url = ?, tags = ?
    WHERE id = ?
    """, (
        p["name"], p["category"], p["address"], float(p["lat"]), float(p["lon"]),
        p.get("open_time", "08:00"), p.get("close_time", "22:00"),
        int(p.get("min_price", 30000)), int(p.get("max_price", 100000)),
        float(p.get("rating", 4.5)), p.get("image_url", ""),
        p.get("tags", "nhom_ban"), int(place_id)
    ))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def delete_place(place_id: int):
    """Xóa địa điểm theo ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM places WHERE id = ?", (int(place_id),))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def migrate_verification_columns():
    """Bổ sung cột is_verified và is_verified_review nếu chưa có"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(places)")
    cols = [r["name"] for r in cursor.fetchall()]
    if "is_verified" not in cols:
        cursor.execute("ALTER TABLE places ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 1")
    if "is_verified_review" not in cols:
        cursor.execute("ALTER TABLE places ADD COLUMN is_verified_review INTEGER NOT NULL DEFAULT 1")
    conn.commit()
    conn.close()

migrate_verification_columns()

def migrate_two_stream_reviews():
    """Bổ sung cột best_review và worst_review cho đánh giá 2 luồng"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(places)")
    cols = [r["name"] for r in cursor.fetchall()]
    if "best_review" not in cols:
        cursor.execute("ALTER TABLE places ADD COLUMN best_review TEXT DEFAULT 'Quán sạch sẽ, đồ ăn ngon, phục vụ nhanh.'")
    if "worst_review" not in cols:
        cursor.execute("ALTER TABLE places ADD COLUMN worst_review TEXT DEFAULT 'Giờ cao điểm hơi đông khách, nên đi sớm.'")
    conn.commit()
    conn.close()

migrate_two_stream_reviews()

def toggle_favorite(user_id: int, place_id: int) -> bool:
    """Thêm hoặc xóa địa điểm khỏi danh sách yêu thích của người dùng"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM favorites WHERE user_id = ? AND place_id = ?", (user_id, place_id))
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM favorites WHERE id = ?", (row["id"],))
        is_saved = False
    else:
        cursor.execute("INSERT INTO favorites (user_id, place_id) VALUES (?, ?)", (user_id, place_id))
        is_saved = True
    conn.commit()
    conn.close()
    return is_saved

def get_user_favorites(user_id: int) -> list:
    """Lấy danh sách các địa điểm đã lưu của người dùng"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.* FROM places p
    INNER JOIN favorites f ON p.id = f.place_id
    WHERE f.user_id = ?
    ORDER BY f.saved_at DESC
    """, (user_id,))
    places = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return places
