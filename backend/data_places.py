# data_places.py

districts = ["Quận 1", "Quận 3", "Quận 5", "Quận 10", "Bình Thạnh", "Phú Nhuận"]

eat_names = [
    "Ốc Chảo Cay Sài Gòn", "Bún Bò Mê Ly", "Lẩu Bò Cư Xá", "Bánh Tráng Nướng Đà Lạt",
    "Bánh Mì Chảo Hẻm", "Cơm Tấm Đêm Bà Mười", "Mì Trộn Xá Xíu Xíu", "Nướng Ngói Khói Lam",
    "Bánh Canh Cua Chợ Thiếc", "Dimsum Tiến Phát", "Phở Thảo Pasteur", "Hủ Tiếu Nam Vang Nam Xuân"
]

play_names = [
    "The Hideout Cafe Chill", "Góc Rooftop Hoàng Hôn", "Boardgame Station Station",
    "Triển Lãm Tranh Art Space", "Bắn Cung Tên Đối Kháng", "Bida Xì-Tin Club",
    "Tiệm Gốm Bát Tràng Sài Gòn", "Workshop Nến Thơm Chill", "Cà Phê Mèo Meo Meo",
    "Bảo Tàng Mỹ Thuật TP.HCM"
]

MOCK_PLACES = []

# Tọa độ gốc trung tâm Sài Gòn để tính toán khoảng cách
base_lat = 10.7769
base_lng = 106.7009

for i in range(1, 101):
    is_eat = (i % 2 == 0)
    category = "an_uong" if is_eat else "di_choi"
    name_list = eat_names if is_eat else play_names
    district = districts[i % len(districts)]
    
    # Phân bổ ngữ cảnh
    if i % 3 == 0:
        context = "nguoi_yeu"
    elif i % 3 == 1:
        context = "nhom_ban"
    else:
        context = "gia_dinh"
        
    price_level = (i % 3) + 1  # 1: <50k, 2: 50k-150k, 3: >150k
    rating = round(4.0 + (i % 10) * 0.1, 1)
    
    # Tạo độ lệch GPS giả lập theo bán kính Sài Gòn (~3-7km)
    lat_offset = ((i * 17) % 50 - 25) * 0.0015
    lng_offset = ((i * 23) % 50 - 25) * 0.0015
    
    MOCK_PLACES.append({
        "id": f"SG-{i:03d}",
        "name": f"{name_list[i % len(name_list)]} #{i}",
        "category": category,
        "context": context,
        "district": district,
        "price_level": price_level,
        "rating": rating,
        "latitude": round(base_lat + lat_offset, 6),
        "longitude": round(base_lng + lng_offset, 6),
        "address": f"Số {(i * 7) % 150 + 1} Đường số {(i % 20) + 1}, {district}, TP.HCM",
        "open_time": "08:00 - 22:30",
        "tag": "Không gian thoáng đãng, đồ uống ngon" if is_eat else "Hoạt động thú vị, giải trí nhóm"
    })