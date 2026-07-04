# WikiBFS - Trình Khám Phá Liên Kết Wikidata

WikiBFS là một ứng dụng web giúp tìm kiếm và hiển thị đường nối ngắn nhất giữa hai thực thể trên Wikidata (người, tổ chức, v.v.) sử dụng thuật toán Breadth-First Search (BFS).

## Tính năng
- **Tìm kiếm BFS**: Tìm đường đi ngắn nhất giữa hai thực thể Wikidata qua các mối quan hệ.
- **Đồ thị tương tác**: Hiển thị đường đi dưới dạng đồ thị 2D sinh động (phong cách GitNexus).
- **Chế độ tối (Dark Mode)**: Giao diện hiện đại, dễ nhìn.
- **Lịch sử tìm kiếm**: Lưu lại các lần tìm kiếm gần đây.

## Cấu trúc dự án
- `backend/`: API FastAPI xử lý logic BFS và truy vấn Wikidata.
- `frontend/`: Ứng dụng React (Vite) hiển thị giao diện người dùng.

## Hướng dẫn cài đặt

### 1. Backend
Yêu cầu Python 3.9+
```bash
cd NAME-RELATED-SEARCHING/backend
# Tạo và kích hoạt môi trường ảo
python3 -m venv venv
source venv/bin/activate  # Trên Linux/macOS
# venv\Scripts\activate  # Trên Windows

# Cài đặt dependencies
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Backend sẽ chạy tại: `http://localhost:8000`

### 2. Frontend
Yêu cầu Node.js 16+
```bash
cd NAME-RELATED-SEARCHING/frontend
npm install
npm run dev
```
Frontend sẽ chạy tại: `http://localhost:5173`

## Chạy toàn bộ dự án bằng Docker Compose (Production Setup)

Hệ thống được cấu hình chạy Production với Nginx làm cổng đảo ngược (Reverse Proxy), định tuyến luồng dữ liệu thời gian thực (SSE) và phục vụ trực tiếp file tĩnh của React Frontend.

Từ thư mục gốc repository, thực thi các lệnh sau:

1. **Khởi chạy hệ thống**:
   ```bash
   docker compose up -d --build
   ```

2. **Kiểm tra trạng thái các service mạng**:
   ```bash
   docker compose ps
   ```

3. **Theo dõi log backend thời gian thực**:
   ```bash
   docker compose logs -f backend
   ```

Các dịch vụ sẽ chạy tại:
- **Frontend & API Gateway**: `http://localhost` (Cổng 80 phục vụ React và chuyển tiếp `/api` an toàn).
- **Backend API thực tế**: `http://localhost/api/` (Định tuyến nội bộ tới `backend:8000`).
- **Luồng dữ liệu thời gian thực (SSE)**: `http://localhost/api/search/stream` (Bật truyền dẫn trực tiếp, không đệm buffer).
- **Redis Cache**: Chạy nội bộ phục vụ backend, được kiểm tra trạng thái sức khỏe (Healthcheck) trước khi khởi động ứng dụng.

## Cách sử dụng
1. Tìm Wikidata ID của hai người bạn muốn liên kết (ví dụ: `Q34660` cho J.K. Rowling).
2. Nhập ID bắt đầu và ID đích vào thanh tìm kiếm.
3. Nhấn "TÌM KIẾM PATH" và đợi kết quả hiển thị trên đồ thị.

## Công nghệ sử dụng
- **Backend**: FastAPI, Requests, Breadth-First Search.
- **Frontend**: React, Vite, React Force Graph, Lucide React, Axios.
- **Dữ liệu**: Wikidata SPARQL API.

## Triển khai (Deployment)

Dự án này có thể được triển khai miễn phí trên Render (Backend) và Vercel (Frontend).

### Backend (Render)
1. Tạo một "Web Service" mới trên Render và kết nối với repo GitHub của bạn.
2. Render sẽ tự động nhận diện `Dockerfile` trong thư mục `NAME-RELATED-SEARCHING/backend`.
3. Trong phần **Environment Variables**, thêm:
   - `REDIS_URL`: URL từ Upstash Redis (ví dụ: `redis://default:password@host:port`).
   - `PORT`: `8000` (Render sẽ tự động ánh xạ).

### Frontend (Vercel)
1. Tạo một dự án mới trên Vercel và kết nối với repo GitHub của bạn.
2. Đặt **Root Directory** là `NAME-RELATED-SEARCHING/frontend`.
3. Trong phần **Environment Variables**, thêm:
   - `VITE_API_BASE_URL`: URL của backend đã triển khai trên Render (ví dụ: `https://your-app.onrender.com/api`).
4. Vercel sẽ tự động build và triển khai ứng dụng React của bạn.
