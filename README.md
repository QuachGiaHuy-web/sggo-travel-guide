# SGGo! - Cẩm Nang Du Lịch & Lộ Trình Thông Minh Sài Gòn

Dự án môn học: **Công nghệ Phần mềm (COMP1044)**  
Nhóm sinh viên thực hiện: SGGo Team  
Trưởng nhóm: Quách Gia Huy  

## 1. Giới thiệu
SGGo! là nền tảng web hướng dẫn du lịch và đề xuất lộ trình văn hóa - ẩm thực thông minh tại TP.HCM. Giai đoạn thử nghiệm tập trung chuyên sâu vào khu vực Quận 5 (Chợ Lớn) với kho 40 địa điểm di sản và ẩm thực lâu đời.

## 2. Hướng dẫn cài đặt & khởi chạy Backend
```bash
# Cài đặt môi trường ảo Python
python -m venv venv
venv\Scripts\activate  # Trên Windows

# Cài đặt thư viện phụ thuộc
pip install -r backend/requirements.txt

# Khởi chạy server API (Uvicorn)
uvicorn backend.main:app --reload --port 8000
```
Truy cập tài liệu API tự động tại: `http://localhost:8000/docs`

## 3. Kiến Trúc Hệ Thống & Tính Năng Nổi Bật
- **Hệ thống bản đồ tương tác (Leaflet + OpenStreetMap):** Ghim 40+ địa điểm đặc trưng với icon tùy biến, lọc theo danh mục, tính khoảng cách thực tế.
- **Thuật toán tối ưu lộ trình (Nearest Neighbor):** Tự động sắp xếp thứ tự ghé thăm nhiều trạm để giảm thiểu quãng đường di chuyển (bài toán TSP).
- **Trợ lý văn hóa thông minh (Google Gemini AI + Offline Heuristic):** Gợi ý lịch trình cá nhân hóa dựa trên giờ rảnh, đối tượng đi cùng và ngân sách, kèm lời bình văn hóa bản địa sâu sắc.
- **Phân quyền người dùng & CSDL SQLite:** Hỗ trợ đăng ký, đăng nhập, lưu địa điểm yêu thích, quản trị địa điểm CRUD và trích xuất tọa độ Google Maps tự động.
- **Đặc tả & Kiểm thử chuyên nghiệp:** Đầy đủ sơ đồ Use Case, Activity Diagram, BPMN 2.0.2 và bộ test tự động pytest.

## 4. Hướng dẫn chạy kiểm thử
```bash
pytest tests/ -v
```
