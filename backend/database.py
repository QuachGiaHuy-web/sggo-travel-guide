# -*- coding: utf-8 -*-
"""
database.py - QUẢN LÝ CƠ SỞ DỮ LIỆU SQLITE CHO DỰ ÁN SGGO!
Môn học: Công nghệ Phần mềm (COMP1044)

Kiến trúc chuẩn CNPM:
- Bảng users: Quản lý đăng ký, đăng nhập và phân quyền (Admin / User thường).
- Bảng places: Quản lý thông tin 40+ địa điểm thực tế tại Quận 5.
- Bảng favorites: Quản lý danh sách địa điểm yêu thích của từng người dùng.
- Hỗ trợ đầy đủ các thao tác CRUD và Import/Export file CSV có kiểm tra dữ liệu.
"""

import os
import sqlite3
import csv
import io
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "sggo.db")
ENRICHED_JSON_PATH = os.path.join(os.path.dirname(__file__), "enriched_places.json")

def get_connection():
    """Tạo kết nối tới file SQLite, trả về sqlite3.Row để truy xuất dữ liệu theo tên cột"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Khởi tạo cấu trúc các bảng và nạp dữ liệu mẫu ban đầu"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. BẢNG USERS (Tài khoản & Phân quyền)
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

    # 2. BẢNG PLACES (Thông tin địa điểm thực tế tại Quận 5)
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
        peak_hours TEXT DEFAULT '18:00 - 20:00',
        best_review TEXT DEFAULT 'Quán sạch sẽ, đồ ăn ngon, phục vụ nhanh.',
        worst_review TEXT DEFAULT 'Giờ cao điểm hơi đông khách, nên đi sớm.',
        image_url TEXT,
        tags TEXT DEFAULT 'nhom_ban',          -- Danh sách tag: di_1_minh, hen_ho, nhom_ban, gia_dinh
        is_verified INTEGER NOT NULL DEFAULT 1, -- 1: Đã xác thực, 0: Chưa duyệt
        is_verified_review INTEGER NOT NULL DEFAULT 1,
        is_admin_choice INTEGER NOT NULL DEFAULT 0 -- 1: Quán Admin yêu thích, 0: Thường
    );
    """)

    # Tự động migrate cột is_admin_choice nếu dùng CSDL cũ
    cursor.execute("PRAGMA table_info(places)")
    existing_cols = [r["name"] for r in cursor.fetchall()]
    if "is_admin_choice" not in existing_cols:
        cursor.execute("ALTER TABLE places ADD COLUMN is_admin_choice INTEGER DEFAULT 0")
        conn.commit()
    if "is_hidden" not in existing_cols:
        cursor.execute("ALTER TABLE places ADD COLUMN is_hidden INTEGER DEFAULT 0")
        conn.commit()

    # 3. BẢNG FAVORITES (Địa điểm yêu thích của người dùng)
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

    # Khởi tạo dữ liệu mẫu nếu bảng còn trống
    seed_users_if_needed(conn)
    seed_places_if_needed(conn)
    conn.close()

def seed_users_if_needed(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO users (username, password, full_name, role) VALUES 
        ('admin', 'admin123', 'Quản Trị Viên SGGo', 'admin'),
        ('user1', '123456', 'Nguyễn Văn A', 'user');
        """)
        conn.commit()

def seed_places_if_needed(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM places")
    if cursor.fetchone()[0] > 0:
        return

    # Đọc 40 quán thực tế từ enriched_places.json
    places_to_insert = []
    if os.path.exists(ENRICHED_JSON_PATH):
        with open(ENRICHED_JSON_PATH, "r", encoding="utf-8") as f:
            raw_places = json.load(f)
            
            for p in raw_places:
                name = p.get("name")
                if not name:
                    continue
                category = p.get("category", "an_uong")
                addr = p.get("address") or p.get("full_address") or "Quận 5, TP.HCM"
                district = p.get("district", "Quận 5")
                lat = float(p.get("lat", 10.7550))
                lon = float(p.get("lon", 106.6650))
                open_time = p.get("open_time", "08:00")
                close_time = p.get("close_time", "22:00")
                min_price = int(p.get("min_price", 30000))
                max_price = int(p.get("max_price", 100000))
                rating = float(p.get("rating", 4.5))
                reviews_count = int(p.get("reviews_count", 100))
                peak_hours = p.get("peak_hours", "18:00 - 20:00")
                best_review = p.get("best_review") or ""
                worst_review = p.get("worst_review") or ""
                img = p.get("image_url") or None
                tags = p.get("tags", "nhom_ban,di_1_minh")
                is_verified = 1

                places_to_insert.append((
                    name, category, addr, district, lat, lon, open_time, close_time,
                    min_price, max_price, rating, reviews_count, peak_hours,
                    best_review, worst_review, img, tags, is_verified
                ))

    if places_to_insert:
        cursor.executemany("""
        INSERT INTO places (
            name, category, address, district, lat, lon, open_time, close_time,
            min_price, max_price, rating, reviews_count, peak_hours,
            best_review, worst_review, image_url, tags, is_verified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, places_to_insert)
        conn.commit()

def sync_db_to_json():
    """Tự động đồng bộ toàn bộ địa điểm từ SQLite ra file JSON để mang sang máy khác không bị mất"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM places ORDER BY id ASC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        with open(ENRICHED_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[WARN] sync_db_to_json error:", e)


# ==============================================================================
# THAO TÁC NGƯỜI DÙNG & TÀI KHOẢN (AUTH)
# ==============================================================================

def authenticate_user(username, password):
    """Kiểm tra thông tin đăng nhập"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, role FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def register_user(username, password, full_name):
    """Đăng ký tài khoản mới"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, 'user')", 
                       (username, password, full_name))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"id": user_id, "username": username, "full_name": full_name, "role": "user"}
    except sqlite3.IntegrityError:
        conn.close()
        return None

def get_all_users():
    """Lấy danh sách tất cả người dùng trong hệ thống (dành cho Admin)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, role, created_at FROM users ORDER BY id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def update_user_role(user_id, new_role):
    """Cập nhật vai trò (admin/user) của người dùng"""
    if new_role not in ['admin', 'user']:
        return False, "Vai trò không hợp lệ (chỉ chấp nhận 'admin' hoặc 'user')"
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Kiểm tra xem có phải hạ quyền của admin duy nhất không
    if new_role == 'user':
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        curr = cursor.fetchone()
        if curr and curr['role'] == 'admin' and admin_count <= 1:
            conn.close()
            return False, "Không thể chuyển admin cuối cùng thành user (cần giữ ít nhất 1 admin)"
            
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    return True, "Cập nhật vai trò thành công"

def delete_user(user_id):
    """Xóa tài khoản người dùng"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Không cho phép xóa admin duy nhất
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    target = cursor.fetchone()
    if not target:
        conn.close()
        return False, "Tài khoản không tồn tại"
        
    if target['role'] == 'admin':
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        if admin_count <= 1:
            conn.close()
            return False, "Không thể xóa admin cuối cùng của hệ thống"
            
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    cursor.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True, "Xóa tài khoản thành công"

# ==============================================================================
# THAO TÁC ĐỊA ĐIỂM (PLACES CRUD)
# ==============================================================================

def get_all_places(category=None, context_tag=None, min_budget=None, max_budget=None, min_rating=None, search=None, only_verified=True):
    """Lấy danh sách địa điểm theo bộ lọc đa chiều (A đến Z)"""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM places WHERE is_hidden = 0"
    params = []

    if only_verified:
        query += " AND is_verified = 1"

    if category and category != "all":
        query += " AND category = ?"
        params.append(category)

    if context_tag and context_tag != "all":
        query += " AND tags LIKE ?"
        params.append(f"%{context_tag}%")

    if min_budget and int(min_budget) > 0:
        query += " AND max_price >= ?"
        params.append(int(min_budget))

    if max_budget and int(max_budget) > 0:
        query += " AND min_price <= ?"
        params.append(int(max_budget))

    if min_rating and float(min_rating) > 0:
        query += " AND rating >= ?"
        params.append(float(min_rating))

    if search:
        query += " AND (name LIKE ? OR address LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY rating DESC, reviews_count DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_place_by_id(place_id):
    """Lấy chi tiết 1 địa điểm"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM places WHERE id = ?", (place_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_place(data):
    """Thêm một địa điểm mới vào CSDL"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO places (
        name, category, address, district, lat, lon, open_time, close_time,
        min_price, max_price, rating, reviews_count, peak_hours,
        best_review, worst_review, image_url, tags, is_verified, is_verified_review, is_admin_choice
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name"),
        data.get("category", "an_uong"),
        data.get("address", "Quận 5, TP.HCM"),
        data.get("district", "Quận 5"),
        float(data.get("lat", 10.7550)),
        float(data.get("lon", 106.6650)),
        data.get("open_time", "08:00"),
        data.get("close_time", "22:00"),
        int(data.get("min_price", 30000)),
        int(data.get("max_price", 100000)),
        float(data.get("rating", 4.5)),
        int(data.get("reviews_count", 50)),
        data.get("peak_hours", "18:00 - 20:00"),
        data.get("best_review") or "",
        data.get("worst_review") or "",
        data.get("image_url") or None,
        data.get("tags", "nhom_ban"),
        int(data.get("is_verified", 1)),
        int(data.get("is_verified_review", 1)),
        int(data.get("is_admin_choice", 0))
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    sync_db_to_json()
    return get_place_by_id(new_id)

def update_place(place_id, data):
    """Cập nhật thông tin địa điểm đã có trong SQLite"""
    existing = get_place_by_id(place_id)
    if not existing:
        return None

    raw_img = data.get("image_url")
    img_val = raw_img.strip() if raw_img and str(raw_img).strip() else None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE places SET
        name = ?, category = ?, address = ?, district = ?,
        lat = ?, lon = ?, open_time = ?, close_time = ?,
        min_price = ?, max_price = ?, rating = ?, reviews_count = ?,
        peak_hours = ?, best_review = ?, worst_review = ?,
        image_url = ?, tags = ?, is_verified = ?, is_verified_review = ?,
        is_admin_choice = ?
    WHERE id = ?
    """, (
        data.get("name", existing.get("name")),
        data.get("category", existing.get("category")),
        data.get("address", existing.get("address")),
        data.get("district", existing.get("district", "Quận 5")),
        float(data.get("lat", existing.get("lat", 10.7550))),
        float(data.get("lon", existing.get("lon", 106.6650))),
        data.get("open_time", existing.get("open_time", "08:00")),
        data.get("close_time", existing.get("close_time", "22:00")),
        int(data.get("min_price", existing.get("min_price", 30000))),
        int(data.get("max_price", existing.get("max_price", 100000))),
        float(data.get("rating", existing.get("rating", 4.5))),
        int(data.get("reviews_count", existing.get("reviews_count", 100))),
        data.get("peak_hours", existing.get("peak_hours", "18:00 - 20:00")),
        data.get("best_review", existing.get("best_review", "")) or "",
        data.get("worst_review", existing.get("worst_review", "")) or "",
        img_val,
        data.get("tags", existing.get("tags", "nhom_ban")),
        int(data.get("is_verified", existing.get("is_verified", 1))),
        int(data.get("is_verified_review", existing.get("is_verified_review", 1))),
        int(data.get("is_admin_choice", existing.get("is_admin_choice", 0))),
        place_id
    ))
    conn.commit()
    conn.close()
    sync_db_to_json()
    return get_place_by_id(place_id)

def delete_place(place_id):
    """Xóa một địa điểm"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM places WHERE id = ?", (place_id,))
    conn.commit()
    conn.close()
    sync_db_to_json()
    return True

# ==============================================================================
# THAO TÁC ĐỊA ĐIỂM YÊU THÍCH (FAVORITES)
# ==============================================================================

def toggle_favorite(user_id, place_id):
    """Thêm hoặc hủy lưu địa điểm yêu thích"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM favorites WHERE user_id = ? AND place_id = ?", (user_id, place_id))
    fav = cursor.fetchone()
    if fav:
        cursor.execute("DELETE FROM favorites WHERE id = ?", (fav["id"],))
        action = "removed"
    else:
        cursor.execute("INSERT INTO favorites (user_id, place_id) VALUES (?, ?)", (user_id, place_id))
        action = "added"
    conn.commit()
    conn.close()
    return action

def get_user_favorites(user_id):
    """Lấy danh sách các địa điểm yêu thích của người dùng"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.* FROM places p
    JOIN favorites f ON p.id = f.place_id
    WHERE f.user_id = ?
    ORDER BY f.saved_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==============================================================================
# NHẬP XUẤT CSV (IMPORT / EXPORT)
# ==============================================================================

def generate_sample_csv():
    """Tạo nội dung file CSV mẫu chuẩn cho Admin tải về điền (an toàn tuyệt đối với mọi dấu phẩy)"""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow([
        "name", "category", "address", "open_time", "close_time", 
        "min_price", "max_price", "rating", "reviews_count", "peak_hours",
        "best_review", "worst_review", "tags", "lat", "lon"
    ])
    writer.writerow([
        "Hủ Tiếu Nam Vang Triều Châu", "an_uong", "85 Trần Bình Trọng, Phường 1, Quận 5", "06:30", "22:00",
        40000, 75000, 4.6, 820, "18:00 - 19:30",
        "Nước dùng ngọt xương tự nhiên, sườn mềm tôm tươi", "Quán giờ tan tầm hơi đông", "nhom_ban,di_1_minh", 10.7570, 106.6780
    ])
    writer.writerow([
        "Cà Phê Trầm Chợ Lớn", "di_choi", "142 Triệu Quang Phục, Phường 11, Quận 5", "08:00", "22:30",
        35000, 65000, 4.5, 430, "15:00 - 17:00",
        "Không gian hoài cổ, nhạc nhẹ, rất hợp học bài và hẹn hò", "Hẻm hơi nhỏ", "hen_ho,di_1_minh", 10.7540, 106.6610
    ])
    return output.getvalue()

def import_csv_data(csv_text):
    """Đọc dữ liệu từ file CSV tải lên và nạp vào CSDL với khả năng tự phục hồi lỗi kiểu dữ liệu"""
    f = io.StringIO(csv_text)
    reader = csv.DictReader(f)
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    for row in reader:
        name = row.get("name")
        if not name:
            continue

        try:
            lat = float(row.get("lat") or 10.7550)
        except (ValueError, TypeError):
            lat = 10.7550

        try:
            lon = float(row.get("lon") or 106.6650)
        except (ValueError, TypeError):
            lon = 106.6650

        try:
            min_price = int(float(row.get("min_price") or 30000))
        except (ValueError, TypeError):
            min_price = 30000

        try:
            max_price = int(float(row.get("max_price") or 80000))
        except (ValueError, TypeError):
            max_price = 80000

        try:
            rating = float(row.get("rating") or 4.5)
        except (ValueError, TypeError):
            rating = 4.5

        try:
            reviews_count = int(float(row.get("reviews_count") or 50))
        except (ValueError, TypeError):
            reviews_count = 50

        category = row.get("category", "an_uong")
        if category not in ["an_uong", "di_choi"]:
            category = "an_uong"

        cursor.execute("""
        INSERT INTO places (
            name, category, address, district, lat, lon, open_time, close_time,
            min_price, max_price, rating, reviews_count, peak_hours,
            best_review, worst_review, image_url, tags, is_verified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name.strip(),
            category,
            row.get("address", "Quận 5, TP.HCM"),
            "Quận 5",
            lat,
            lon,
            row.get("open_time", "08:00"),
            row.get("close_time", "22:00"),
            min_price,
            max_price,
            rating,
            reviews_count,
            row.get("peak_hours", "18:00 - 20:00"),
            row.get("best_review") or "",
            row.get("worst_review") or "",
            row.get("image_url") or None,
            row.get("tags", "nhom_ban"),
            1
        ))
        count += 1

    conn.commit()
    conn.close()
    sync_db_to_json()
    return count

def toggle_hide_place(place_id: int, is_hidden: int = 1) -> bool:
    """Toggle ẩn/hiện một địa điểm (G6-FR01 & G6-FR08)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE places SET is_hidden = ? WHERE id = ?", (is_hidden, place_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success
