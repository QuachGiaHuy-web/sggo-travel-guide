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
        is_admin_choice INTEGER NOT NULL DEFAULT 0, -- 1: Quán Admin yêu thích, 0: Thường
        is_hidden INTEGER NOT NULL DEFAULT 0, -- 1: Quán bị ẩn, 0: Bình thường
        google_maps_url TEXT                  -- Link Google Maps thực tế để đối chiếu và điều hướng
    );
    """)

    # Tự động migrate cột is_admin_choice và is_hidden nếu dùng CSDL cũ
    cursor.execute("PRAGMA table_info(places)")
    existing_cols = [r["name"] for r in cursor.fetchall()]
    if "is_admin_choice" not in existing_cols:
        cursor.execute("ALTER TABLE places ADD COLUMN is_admin_choice INTEGER DEFAULT 0")
        conn.commit()
    if "is_hidden" not in existing_cols:
        cursor.execute("ALTER TABLE places ADD COLUMN is_hidden INTEGER DEFAULT 0")
        conn.commit()
    if "google_maps_url" not in existing_cols:
        cursor.execute("ALTER TABLE places ADD COLUMN google_maps_url TEXT")
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

    # 4. BẢNG ITINERARIES (Lưu trữ lịch trình theo yêu cầu Section 5 đề tài)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itineraries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        start_location TEXT NOT NULL,
        start_lat REAL,
        start_lon REAL,
        free_time TEXT NOT NULL,
        companion TEXT DEFAULT 'ban_be',
        purpose TEXT DEFAULT 'ca_hai',
        budget_level TEXT DEFAULT '100k_250k',
        target_budget INTEGER DEFAULT 250000,
        total_estimated_budget_min INTEGER DEFAULT 0,
        total_estimated_budget_max INTEGER DEFAULT 0,
        total_duration_minutes INTEGER DEFAULT 0,
        summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    # 5. BẢNG ITINERARY_STOPS (Các chặng dừng trong lịch trình theo yêu cầu Section 5 đề tài)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itinerary_stops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        itinerary_id INTEGER NOT NULL,
        place_id INTEGER NOT NULL,
        stop_order INTEGER NOT NULL,
        time_slot TEXT,
        action_title TEXT,
        travel_distance_km REAL,
        travel_time_minutes INTEGER,
        estimated_cost_min INTEGER DEFAULT 0,
        estimated_cost_max INTEGER DEFAULT 0,
        FOREIGN KEY (itinerary_id) REFERENCES itineraries(id) ON DELETE CASCADE,
        FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE
    );
    """)

    # 6. BẢNG IMPORT_LOGS (Lịch sử nạp CSV & Báo cáo dòng lỗi theo yêu cầu G6-FR09 & Section 5)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS import_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL DEFAULT 'uploaded_places.csv',
        total_rows INTEGER NOT NULL DEFAULT 0,
        success_count INTEGER NOT NULL DEFAULT 0,
        error_count INTEGER NOT NULL DEFAULT 0,
        error_details_json TEXT,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 7. BẢNG TAGS (Danh mục thẻ ngữ cảnh theo yêu cầu G6-FR08 & Section 5 ERD)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag_key TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        tier_type TEXT DEFAULT 'companion',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 8. BẢNG PLACE_TAGS (Bảng quan hệ nhiều-nhiều giữa Place và Tag theo Section 5 ERD)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS place_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        tier INTEGER DEFAULT 1,
        FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
        UNIQUE(place_id, tag_id)
    );
    """)

    conn.commit()

    # Khởi tạo dữ liệu mẫu nếu bảng còn trống
    seed_users_if_needed(conn)
    seed_places_if_needed(conn)
    seed_tags_if_needed(conn)
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


def seed_tags_if_needed(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tags")
    if cursor.fetchone()[0] == 0:
        default_tags = [
            ("nhom_ban", "Nhóm bạn thân", "companion"),
            ("hen_ho", "Cặp đôi / Hẹn hò", "companion"),
            ("gia_dinh", "Gia đình / Người thân", "companion"),
            ("di_1_minh", "Đi một mình (Solo)", "companion"),
        ]
        for k, n, t in default_tags:
            cursor.execute("INSERT OR IGNORE INTO tags (tag_key, name, tier_type) VALUES (?, ?, ?)", (k, n, t))
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM place_tags")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id, tag_key FROM tags")
        tag_map = {row[1]: row[0] for row in cursor.fetchall()}

        cursor.execute("SELECT id, tags FROM places")
        places = cursor.fetchall()
        for pid, tags_str in places:
            if not tags_str:
                continue
            raw_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            for idx, t in enumerate(raw_tags):
                tag_id = tag_map.get(t)
                if tag_id:
                    tier = 1 if idx < 2 else 2
                    cursor.execute("INSERT OR IGNORE INTO place_tags (place_id, tag_id, tier) VALUES (?, ?, ?)", (pid, tag_id, tier))
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

def get_all_places(category=None, context_tag=None, min_budget=None, max_budget=None, min_rating=None, search=None, only_verified=True, include_hidden=False):
    """Lấy danh sách địa điểm theo bộ lọc đa chiều (A đến Z)"""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM places WHERE 1=1"
    params = []

    if not include_hidden:
        query += " AND (is_hidden = 0 OR is_hidden IS NULL)"

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

    if max_budget is not None and str(max_budget).strip() != "":
        max_b_val = int(max_budget)
        if max_b_val == 0:
            query += " AND min_price = 0 AND max_price = 0"
        elif max_b_val > 0:
            query += " AND min_price <= ?"
            params.append(max_b_val)

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

def sync_place_tags_record(cursor, place_id: int, tags_str: str):
    """Đồng bộ quan hệ N-N giữa place và tags vào bảng place_tags (Section 5 ERD)"""
    if not place_id or not tags_str:
        return
    cursor.execute("SELECT id, tag_key FROM tags")
    tag_map = {row[1]: row[0] for row in cursor.fetchall()}
    if not tag_map:
        return

    cursor.execute("DELETE FROM place_tags WHERE place_id = ?", (place_id,))
    
    t1_list = []
    t2_list = []
    if "tier1:" in tags_str or "tier2:" in tags_str:
        parts = tags_str.split("|")
        for p in parts:
            p = p.strip()
            if p.startswith("tier1:"):
                t1_list = [x.strip() for x in p.replace("tier1:", "").split(",") if x.strip()]
            elif p.startswith("tier2:"):
                t2_list = [x.strip() for x in p.replace("tier2:", "").split(",") if x.strip()]
    else:
        all_tags = [x.strip() for x in tags_str.split(",") if x.strip()]
        t1_list = all_tags[:2]
        t2_list = all_tags[2:]

    for k in t1_list:
        tid = tag_map.get(k)
        if tid:
            cursor.execute("INSERT OR IGNORE INTO place_tags (place_id, tag_id, tier) VALUES (?, ?, 1)", (place_id, tid))
    for k in t2_list:
        tid = tag_map.get(k)
        if tid:
            cursor.execute("INSERT OR IGNORE INTO place_tags (place_id, tag_id, tier) VALUES (?, ?, 2)", (place_id, tid))

def add_place(data):
    """Thêm một địa điểm mới vào CSDL"""
    conn = get_connection()
    cursor = conn.cursor()
    gmaps_val = data.get("google_maps_url")
    if not gmaps_val and data.get("name") and data.get("address"):
        import urllib.parse
        gmaps_val = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(str(data.get('name')) + ' ' + str(data.get('address')))}"

    cursor.execute("""
    INSERT INTO places (
        name, category, address, district, lat, lon, open_time, close_time,
        min_price, max_price, rating, reviews_count, peak_hours,
        best_review, worst_review, image_url, tags, is_verified, is_verified_review, is_admin_choice,
        price_display, hours_display, is_hidden, google_maps_url
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name"),
        data.get("category", "an_uong"),
        data.get("address") or "TP.HCM",
        data.get("district") or "TP.HCM",
        float(data.get("lat") or 0.0),
        float(data.get("lon") or 0.0),
        data.get("open_time") or "08:00",
        data.get("close_time") or "22:00",
        int(data.get("min_price") or 0),
        int(data.get("max_price") or 0),
        float(data.get("rating") or 4.5),
        int(data.get("reviews_count") or 0),
        data.get("peak_hours", "18:00 - 20:00"),
        data.get("best_review") or "",
        data.get("worst_review") or "",
        data.get("image_url") or None,
        data.get("tags", "nhom_ban"),
        int(data.get("is_verified", 1)),
        int(data.get("is_verified_review", 1)),
        int(data.get("is_admin_choice", 0)),
        data.get("price_display"),
        data.get("hours_display"),
        int(data.get("is_hidden", 0)),
        gmaps_val
    ))
    new_id = cursor.lastrowid
    sync_place_tags_record(cursor, new_id, data.get("tags", "nhom_ban"))
    conn.commit()
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
    gmaps_val = data.get("google_maps_url", existing.get("google_maps_url"))
    if not gmaps_val and data.get("name") and data.get("address"):
        import urllib.parse
        gmaps_val = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(str(data.get('name')) + ' ' + str(data.get('address')))}"

    cursor.execute("""
    UPDATE places SET
        name = ?, category = ?, address = ?, district = ?,
        lat = ?, lon = ?, open_time = ?, close_time = ?,
        min_price = ?, max_price = ?, rating = ?, reviews_count = ?,
        peak_hours = ?, best_review = ?, worst_review = ?,
        image_url = ?, tags = ?, is_verified = ?, is_verified_review = ?,
        is_admin_choice = ?, price_display = ?, hours_display = ?, is_hidden = ?,
        google_maps_url = ?
    WHERE id = ?
    """, (
        data.get("name", existing.get("name")),
        data.get("category", existing.get("category")),
        data.get("address", existing.get("address")),
        data.get("district", existing.get("district", "TP.HCM")),
        float(data.get("lat") if data.get("lat") is not None else existing.get("lat", 0.0)),
        float(data.get("lon") if data.get("lon") is not None else existing.get("lon", 0.0)),
        data.get("open_time", existing.get("open_time", "08:00")),
        data.get("close_time", existing.get("close_time", "22:00")),
        int(data.get("min_price") if data.get("min_price") is not None else existing.get("min_price", 0)),
        int(data.get("max_price") if data.get("max_price") is not None else existing.get("max_price", 0)),
        float(data.get("rating") if data.get("rating") is not None else existing.get("rating", 4.5)),
        int(data.get("reviews_count") if data.get("reviews_count") is not None else existing.get("reviews_count", 0)),
        data.get("peak_hours", existing.get("peak_hours", "18:00 - 20:00")),
        data.get("best_review", existing.get("best_review", "")) or "",
        data.get("worst_review", existing.get("worst_review", "")) or "",
        img_val,
        data.get("tags", existing.get("tags", "nhom_ban")),
        int(data.get("is_verified", existing.get("is_verified", 1))),
        int(data.get("is_verified_review", existing.get("is_verified_review", 1))),
        int(data.get("is_admin_choice", existing.get("is_admin_choice", 0))),
        data.get("price_display", existing.get("price_display")),
        data.get("hours_display", existing.get("hours_display")),
        int(data.get("is_hidden", existing.get("is_hidden", 0))),
        gmaps_val,
        place_id
    ))
    sync_place_tags_record(cursor, place_id, data.get("tags", existing.get("tags", "nhom_ban")))
    conn.commit()
    conn.close()
    sync_db_to_json()
    return get_place_by_id(place_id)

def delete_place(place_id):
    """Xóa một địa điểm"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM place_tags WHERE place_id = ?", (place_id,))
    cursor.execute("DELETE FROM places WHERE id = ?", (place_id,))
    conn.commit()
    conn.close()
    sync_db_to_json()
    return True

def toggle_hide_place(place_id):
    """Bật / tắt trạng thái ẩn của địa điểm (Admin Soft Hide)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, is_hidden FROM places WHERE id = ?", (place_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    curr_hidden = row["is_hidden"] if row["is_hidden"] is not None else 0
    new_hidden = 1 if curr_hidden == 0 else 0
    cursor.execute("UPDATE places SET is_hidden = ? WHERE id = ?", (new_hidden, place_id))
    conn.commit()
    conn.close()
    sync_db_to_json()
    return {"id": place_id, "is_hidden": new_hidden}



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
        "best_review", "worst_review", "tags", "lat", "lon", "google_maps_url"
    ])
    writer.writerow([
        "Hủ Tiếu Nam Vang Triều Châu", "an_uong", "85 Trần Bình Trọng, Phường 1, Quận 5", "06:30", "22:00",
        40000, 75000, 4.6, 820, "18:00 - 19:30",
        "Nước dùng ngọt xương tự nhiên, sườn mềm tôm tươi", "Quán giờ tan tầm hơi đông", "nhom_ban,di_1_minh", 10.7570, 106.6780,
        "https://www.google.com/maps/search/?api=1&query=H%E1%BB%A7+Ti%E1%BA%BFu+Nam+Vang+Tri%E1%BB%81u+Ch%C3%A2u+Qu%E1%BA%ADn+5"
    ])
    writer.writerow([
        "Cà Phê Trầm Chợ Lớn", "di_choi", "142 Triệu Quang Phục, Phường 11, Quận 5", "08:00", "22:30",
        35000, 65000, 4.5, 430, "15:00 - 17:00",
        "Không gian hoài cổ, nhạc nhẹ, rất hợp học bài và hẹn hò", "Hẻm hơi nhỏ", "hen_ho,di_1_minh", 10.7540, 106.6610,
        "https://www.google.com/maps/search/?api=1&query=C%C3%A0+Ph%C3%AA+Tr%E1%BA%A7m+Ch%E1%BB%A3+L%E1%BB%9Bn+Qu%E1%BA%ADn+5"
    ])
    return output.getvalue()

def generate_sample_excel():
    """Tạo nội dung file Excel (.xlsx) mẫu chuẩn cho Admin tải về nạp dữ liệu (G6-FR09)"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DS_Dia_Diem_Mau"

    headers = [
        "name", "category", "address", "open_time", "close_time", 
        "min_price", "max_price", "rating", "reviews_count", "peak_hours",
        "best_review", "worst_review", "tags", "lat", "lon", "google_maps_url"
    ]
    ws.append(headers)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="E11D48", end_color="E11D48", fill_type="solid")
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    sample_rows = [
        [
            "Hủ Tiếu Nam Vang Triều Châu", "an_uong", "85 Trần Bình Trọng, Phường 1, Quận 5", "06:30", "22:00",
            40000, 75000, 4.6, 820, "18:00 - 19:30",
            "Nước dùng ngọt xương tự nhiên, sườn mềm tôm tươi", "Quán giờ tan tầm hơi đông", "nhom_ban,di_1_minh", 10.7570, 106.6780,
            "https://www.google.com/maps/search/?api=1&query=H%E1%BB%A7+Ti%E1%BA%BFu+Nam+Vang+Tri%E1%BB%81u+Ch%C3%A2u+Qu%E1%BA%ADn+5"
        ],
        [
            "Cà Phê Trầm Chợ Lớn", "di_choi", "142 Triệu Quang Phục, Phường 11, Quận 5", "08:00", "22:30",
            35000, 65000, 4.5, 430, "15:00 - 17:00",
            "Không gian hoài cổ, nhạc nhẹ, rất hợp học bài và hẹn hò", "Hẻm hơi nhỏ", "hen_ho,di_1_minh", 10.7540, 106.6610,
            "https://www.google.com/maps/search/?api=1&query=C%C3%A0+Ph%C3%AA+Tr%E1%BA%A7m+Ch%E1%BB%A3+L%E1%BB%9Bn+Qu%E1%BA%ADn+5"
        ]
    ]
    for r in sample_rows:
        ws.append(r)

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def parse_rows_from_file_content(data, filename: str):
    """
    Tự động nhận diện định dạng CSV hoặc Excel (.xlsx, .xls) và trích xuất danh sách row dictionaries
    """
    fname_lower = filename.lower()
    is_excel = fname_lower.endswith(".xlsx") or fname_lower.endswith(".xls")

    if is_excel or (isinstance(data, str) and ("base64," in data or (len(data) > 100 and "\n" not in data[:100] and "\r" not in data[:100]))):
        import openpyxl
        import base64
        file_bytes = data
        if isinstance(data, str):
            if "base64," in data:
                data = data.split("base64,")[1]
            try:
                file_bytes = base64.b64decode(data)
            except Exception:
                file_bytes = data.encode("utf-8")
        elif isinstance(data, (bytes, bytearray)):
            file_bytes = data

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        sheet = wb.active
        raw_rows = list(sheet.iter_rows(values_only=True))
        if not raw_rows:
            return []

        header_row = raw_rows[0]
        headers = [str(h).strip().lower() if h is not None else f"col_{i}" for i, h in enumerate(header_row)]

        parsed_rows = []
        for r in raw_rows[1:]:
            if not any(val is not None and str(val).strip() != "" for val in r):
                continue
            row_dict = {}
            for i, val in enumerate(r):
                if i < len(headers):
                    key = headers[i]
                    row_dict[key] = "" if val is None else str(val).strip()
            parsed_rows.append(row_dict)
        return parsed_rows
    else:
        csv_str = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
        f = io.StringIO(csv_str)
        reader = csv.DictReader(f)
        return list(reader)


def import_file_data(data, filename="uploaded_places.csv"):
    """
    Đọc dữ liệu từ file CSV hoặc Excel (.xlsx) tải lên và nạp vào CSDL với kiểm tra lỗi chặt chẽ (G6-FR09 & Business Rule 4):
    - Phát hiện trường bắt buộc bị thiếu (Tên quán, Thể loại, Địa chỉ)
    - Phát hiện kiểu dữ liệu sai (Tọa độ không phải float, Giá tiền không phải số nguyên, Sao không hợp lệ)
    - Ghi nhận chi tiết dòng lỗi để Admin xem và chỉnh sửa (Demo Flow 3)
    - Ghi log lịch sử import vào bảng import_logs (Section 5)
    """
    parsed_rows = parse_rows_from_file_content(data, filename)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT LOWER(TRIM(name)) FROM places")
    existing_names = set(r[0] for r in cursor.fetchall())

    success_count = 0
    errors = []
    row_idx = 1  # Header là dòng 1, dòng dữ liệu đầu tiên là dòng 2

    for row in parsed_rows:
        row_idx += 1
        name = (row.get("name") or "").strip()
        address = (row.get("address") or "").strip()
        category = (row.get("category") or "").strip().lower()

        # 1. Kiểm tra trường bắt buộc
        if not name:
            errors.append({"row": row_idx, "field": "name", "reason": "Thiếu tên địa điểm (trường bắt buộc)"})
            continue

        if not address:
            errors.append({"row": row_idx, "field": "address", "reason": f"Quán '{name}' thiếu địa chỉ cụ thể (trường bắt buộc)"})
            continue

        if category not in ["an_uong", "di_choi"]:
            errors.append({"row": row_idx, "field": "category", "reason": f"Quán '{name}' có thể loại '{category}' không hợp lệ (phải là 'an_uong' hoặc 'di_choi')"})
            continue

        # 2. Kiểm tra kiểu dữ liệu tọa độ
        try:
            lat = float(row.get("lat") or 10.7550)
            if not (8.0 <= lat <= 24.0):
                raise ValueError("Vĩ độ ngoài phạm vi VN")
        except Exception:
            errors.append({"row": row_idx, "field": "lat", "reason": f"Quán '{name}': Vĩ độ (lat) '{row.get('lat')}' không phải số thực hợp lệ"})
            continue

        try:
            lon = float(row.get("lon") or 106.6650)
            if not (102.0 <= lon <= 110.0):
                raise ValueError("Kinh độ ngoài phạm vi VN")
        except Exception:
            errors.append({"row": row_idx, "field": "lon", "reason": f"Quán '{name}': Kinh độ (lon) '{row.get('lon')}' không phải số thực hợp lệ"})
            continue

        # 3. Kiểm tra kiểu dữ liệu mức giá
        try:
            min_price = int(float(row.get("min_price") if row.get("min_price") is not None and str(row.get("min_price")).strip() != "" else 30000))
            if min_price < 0:
                raise ValueError("Giá âm")
        except Exception:
            errors.append({"row": row_idx, "field": "min_price", "reason": f"Quán '{name}': Giá tối thiểu (min_price) '{row.get('min_price')}' phải là số nguyên >= 0"})
            continue

        try:
            max_price = int(float(row.get("max_price") if row.get("max_price") is not None and str(row.get("max_price")).strip() != "" else 80000))
            if max_price < min_price:
                raise ValueError("max_price < min_price")
        except Exception:
            errors.append({"row": row_idx, "field": "max_price", "reason": f"Quán '{name}': Giá tối đa (max_price) '{row.get('max_price')}' phải lớn hơn hoặc bằng giá tối thiểu"})
            continue

        # 4. Kiểm tra số sao đánh giá
        try:
            rating = float(row.get("rating") if row.get("rating") is not None and str(row.get("rating")).strip() != "" else 4.5)
            if not (1.0 <= rating <= 5.0):
                raise ValueError("Rating ngoài 1-5")
        except Exception:
            errors.append({"row": row_idx, "field": "rating", "reason": f"Quán '{name}': Đánh giá sao (rating) '{row.get('rating')}' phải trong khoảng 1.0 đến 5.0"})
            continue

        try:
            reviews_count = int(float(row.get("reviews_count") or 50))
        except Exception:
            reviews_count = 50

        # Kiểm tra trùng lặp
        if name.lower() in existing_names:
            errors.append({"row": row_idx, "field": "name", "reason": f"Địa điểm '{name}' đã tồn tại trong CSDL (bị trùng lặp)"})
            continue

        gmaps_url = (row.get("google_maps_url") or row.get("maps_url") or "").strip()
        if not gmaps_url:
            import urllib.parse
            gmaps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name + ' ' + address)}"

        cursor.execute("""
        INSERT INTO places (
            name, category, address, district, lat, lon, open_time, close_time,
            min_price, max_price, rating, reviews_count, peak_hours,
            best_review, worst_review, image_url, tags, is_verified, is_hidden, google_maps_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
        """, (
            name,
            category,
            address,
            row.get("district") or "TP.HCM",
            lat,
            lon,
            row.get("open_time") or "08:00",
            row.get("close_time") or "22:00",
            min_price,
            max_price,
            rating,
            reviews_count,
            row.get("peak_hours") or "18:00 - 20:00",
            row.get("best_review") or "",
            row.get("worst_review") or "",
            row.get("image_url") or None,
            row.get("tags") or "nhom_ban",
            gmaps_url
        ))
        existing_names.add(name.lower())
        success_count += 1

    total_rows = (row_idx - 1)
    error_count = len(errors)

    # Ghi log lịch sử import vào CSDL (Section 5)
    try:
        cursor.execute("""
        INSERT INTO import_logs (filename, total_rows, success_count, error_count, error_details_json)
        VALUES (?, ?, ?, ?, ?)
        """, (filename, total_rows, success_count, error_count, json.dumps(errors, ensure_ascii=False)))
    except Exception as e:
        print("[WARN] Failed to insert import_log:", e)

    conn.commit()
    conn.close()
    sync_db_to_json()
    return {
        "filename": filename,
        "total_rows": total_rows,
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors
    }


def import_csv_data(csv_text, filename="uploaded_places.csv"):
    """Wrapper tương thích ngược cho import CSV"""
    return import_file_data(csv_text, filename=filename)


def import_excel_data(excel_data, filename="uploaded_places.xlsx"):
    """Wrapper chuyên dụng cho import Excel (.xlsx)"""
    return import_file_data(excel_data, filename=filename)


def save_itinerary(itin_data, stops_data):
    """Lưu lịch trình và các chặng dừng vào CSDL (Section 5 ERD)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO itineraries (
        user_id, start_location, start_lat, start_lon, free_time, companion,
        purpose, budget_level, target_budget, total_estimated_budget_min,
        total_estimated_budget_max, total_duration_minutes, summary
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        itin_data.get("user_id"),
        itin_data.get("start_location"),
        itin_data.get("start_lat"),
        itin_data.get("start_lon"),
        itin_data.get("free_time"),
        itin_data.get("companion", "ban_be"),
        itin_data.get("purpose", "ca_hai"),
        itin_data.get("budget_level", "100k_250k"),
        itin_data.get("target_budget", 250000),
        itin_data.get("total_estimated_budget_min", 0),
        itin_data.get("total_estimated_budget_max", 0),
        itin_data.get("total_duration_minutes", 0),
        itin_data.get("summary", "")
    ))
    itin_id = cursor.lastrowid

    for s in stops_data:
        cursor.execute("""
        INSERT INTO itinerary_stops (
            itinerary_id, place_id, stop_order, time_slot, action_title,
            travel_distance_km, travel_time_minutes, estimated_cost_min, estimated_cost_max
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            itin_id,
            s.get("place_id"),
            s.get("stop_order", 1),
            s.get("time_slot", ""),
            s.get("action_title", ""),
            s.get("travel_distance_km", 0.0),
            s.get("travel_time_minutes", 0),
            s.get("estimated_cost_min", 0),
            s.get("estimated_cost_max", 0)
        ))

    conn.commit()
    conn.close()
    return itin_id

def get_import_logs(limit=10):
    """Lấy danh sách lịch sử nạp CSV gần nhất"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM import_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ==========================================
# QUẢN LÝ TAG & BỘ LỌC (G6-FR08 & Section 5 ERD)
# ==========================================
def get_all_tags():
    """Lấy danh sách tất cả các tag cùng số lượng quán liên kết"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT t.id, t.tag_key, t.name, t.tier_type, t.is_active, t.created_at,
           COUNT(pt.place_id) as place_count
    FROM tags t
    LEFT JOIN place_tags pt ON t.id = pt.tag_id
    GROUP BY t.id
    ORDER BY t.tier_type, t.id
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_tag(tag_key: str, name: str, tier_type: str = "companion"):
    """Thêm một tag mới vào hệ thống"""
    conn = get_connection()
    cursor = conn.cursor()
    clean_key = tag_key.strip().lower().replace(" ", "_")
    try:
        cursor.execute("""
        INSERT INTO tags (tag_key, name, tier_type, is_active)
        VALUES (?, ?, ?, 1)
        """, (clean_key, name.strip(), tier_type))
        conn.commit()
        tag_id = cursor.lastrowid
        conn.close()
        return {"status": "success", "id": tag_id, "tag_key": clean_key, "name": name}
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}

def update_tag(tag_id: int, name: str, is_active: int = 1):
    """Cập nhật tên và trạng thái của tag"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tags SET name = ?, is_active = ? WHERE id = ?
    """, (name.strip(), is_active, tag_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def delete_tag(tag_id: int):
    """Xóa tag khỏi hệ thống (đồng thời xóa liên kết trong place_tags)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM place_tags WHERE tag_id = ?", (tag_id,))
    cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def toggle_tag_active(tag_id: int, is_active: int):
    """Bật/tắt trạng thái sử dụng của tag"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tags SET is_active = ? WHERE id = ?", (is_active, tag_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success
