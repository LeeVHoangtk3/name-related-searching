# Thiết kế Triển khai WikiBFS (Free Deployment Design)

Kế hoạch triển khai dự án WikiBFS sử dụng các dịch vụ miễn phí phổ biến và ổn định.

## 1. Thành phần Triển khai

| Thành phần | Dịch vụ | Đặc điểm |
| :--- | :--- | :--- |
| **Frontend (React)** | **Vercel** hoặc **Netlify** | Tự động deploy từ GitHub, hỗ trợ HTTPS, CDN nhanh. |
| **Backend (FastAPI)** | **Render** | Miễn phí (Free Instance), tự động deploy. *Lưu ý: Sẽ bị sleep sau 15p không hoạt động (spin-up khoảng 30s).* |
| **Database (Redis)** | **Upstash** | Serverless Redis, miễn phí 10k request/ngày, cực kỳ ổn định. |

## 2. Các bước thực hiện

### Bước 1: Thiết lập Redis (Upstash)
1. Truy cập [upstash.com](https://upstash.com/), tạo database Redis miễn phí.
2. Lấy `REDIS_URL` (ví dụ: `redis://default:password@host:port`).

### Bước 2: Chuẩn bị Backend cho Render
1. Tạo file `Dockerfile` hoặc sử dụng Build Command của Render.
2. Cấu hình các biến môi trường (Environment Variables) trên Render:
   - `REDIS_URL`: Lấy từ Upstash.
   - `WIKIDATA_ENDPOINT`: Mặc định.

### Bước 3: Chuẩn bị Frontend cho Vercel
1. Cập nhật `API_BASE_URL` trong `App.jsx` để trỏ đến domain của Render (ví dụ: `https://wikibfs-api.onrender.com/api`).
2. Tốt nhất là sử dụng biến môi trường `VITE_API_BASE_URL`.

### Bước 4: Kết nối GitHub
1. Push toàn bộ code lên GitHub.
2. Kết nối GitHub với Render (cho backend) và Vercel (cho frontend).

## 3. Cấu hình Biến môi trường (Environment Variables)

**Backend (Render):**
- `REDIS_URL=...`
- `PORT=8000` (Render sẽ tự map)

**Frontend (Vercel):**
- `VITE_API_BASE_URL=https://your-backend-url.onrender.com/api`

## 4. Kiểm tra sau khi triển khai
- Kiểm tra kết nối từ Frontend đến Backend.
- Kiểm tra Backend có ghi/đọc được cache từ Upstash hay không.
