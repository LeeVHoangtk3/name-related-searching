# Thiết kế Tích hợp Redis cho WikiBFS

Dự án sẽ sử dụng Redis để tăng tốc độ truy vấn và lưu trữ dữ liệu tìm kiếm toàn cục.

## 1. Mục tiêu
- **Caching**: Lưu kết quả tìm kiếm BFS và danh sách hàng xóm để giảm latency từ Wikidata API.
- **Global History**: Lưu danh sách các lần tìm kiếm gần đây nhất của tất cả người dùng để hiển thị trên frontend.

## 2. Kiến trúc
- **Backend (FastAPI)**: 
  - Sử dụng thư viện `redis-py`.
  - Check Redis trước khi gọi Wikidata API (Cache Aside pattern).
  - Ghi đè/Cập nhật Redis sau khi có kết quả mới.
- **Dữ liệu trong Redis**:
  - `path:{start}:{target}`: Lưu chuỗi JSON của mảng đường đi (TTL: 24h).
  - `neighbors:{id}`: Lưu chuỗi JSON của mảng hàng xóm (TTL: 48h).
  - `global_history`: Sử dụng Redis List (`LPUSH` + `LTRIM`) để lưu 20 lượt tìm kiếm mới nhất.

## 3. Các thành phần mới
- `app/core/redis.py`: Khởi tạo kết nối Redis.
- Cập nhật `app/core/config.py`: Thêm cấu hình `REDIS_URL`.
- Cập nhật `app/api/routes.py`: Logic check cache và lưu lịch sử.

## 4. Kế hoạch triển khai
1. Cài đặt `redis` vào `requirements.txt`.
2. Tạo module kết nối Redis trong backend.
3. Tích hợp caching vào endpoint `/search`.
4. Tạo endpoint mới `/history` để lấy lịch sử toàn cục.
5. Cập nhật Frontend để gọi API lấy lịch sử toàn cục.
