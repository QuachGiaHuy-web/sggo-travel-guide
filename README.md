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
