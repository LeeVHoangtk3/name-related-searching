# Tổng Quan Dự Án: WikiBFS (Name Related Searching)

## 1. Tổng Quan (Overview)
**WikiBFS** là một ứng dụng web cho phép người dùng tìm kiếm, khám phá và hiển thị đường nối ngắn nhất giữa hai thực thể bất kỳ trên Wikidata (ví dụ: người, tổ chức, sự kiện, v.v.). 
Hệ thống sử dụng thuật toán **Breadth-First Search (BFS)** để duyệt qua mạng lưới đồ thị khổng lồ của Wikidata, tìm ra các mối quan hệ liên kết chúng. Dự án được thiết kế với kiến trúc Client-Server (Frontend React và Backend FastAPI), cho phép tương tác thời gian thực thông qua Server-Sent Events (SSE) và tối ưu hóa tốc độ truy xuất bằng Redis cache.

---

## 2. Luồng Hoạt Động (Flow)
Luồng xử lý từ lúc người dùng nhập thông tin đến khi hiển thị kết quả diễn ra như sau:

1. **Gợi ý & Nhập liệu (Input):** Người dùng nhập tên của thực thể bắt đầu và thực thể kết thúc. Frontend sẽ gọi API `/api/suggest` (thông qua `suggestion_service.py`) tới Wikidata để tự động hiển thị gợi ý và map tên văn bản thành **Wikidata ID** (VD: `Q34660`).
2. **Kích hoạt tìm kiếm:** Khi nhấn "Tìm kiếm", Frontend sẽ mở một kết nối **Server-Sent Events (SSE)** tới Backend (`/api/search/...`).
3. **Kiểm tra Cache:** Backend nhận ID, trước tiên kiểm tra trong **Redis Cache** (hoặc `file_cache.py`) xem đường đi giữa 2 ID này đã được tính toán trong quá khứ chưa. Nếu có, dữ liệu được trả về ngay.
4. **Thực thi BFS (Xử lý Đồ thị):** Nếu chưa có cache, `path_service.py` sẽ khởi chạy thuật toán BFS qua `bfs_service.py`. 
   - Hệ thống liên tục gửi các truy vấn SPARQL (`neighbor_wikidata.py`) để lấy tất cả các láng giềng (neighbor) của các node ở độ sâu hiện tại.
   - Trong quá trình này, backend liên tục `yield` (đẩy) tiến trình (Progress) về Frontend thông qua SSE để người dùng biết thuật toán đang quét bao nhiêu node.
5. **Chuẩn hóa & Lưu Cache:** Khi tìm được đường đi ngắn nhất hoặc hết giới hạn tìm kiếm, dữ liệu thô sẽ được đưa qua `normalize.py` để format thành danh sách `nodes` và `links`. Kết quả này được lưu vào Redis để dùng cho lần sau.
6. **Render Giao Diện (Output):** Frontend nhận dữ liệu JSON hoàn chỉnh, sử dụng component `Graph.jsx` (thư viện `react-force-graph-2d`) để vẽ đồ họa 2D minh họa cho đường đi này.

---

## 3. Chức Năng (Functions & Features)
- **Tìm kiếm đồ thị BFS:** Cốt lõi của hệ thống, tìm đường đi ngắn nhất qua các mối quan hệ (Properties) của Wikidata.
- **Autocomplete / Auto-suggestion:** Tự động hoàn thành và tìm ID Wikidata chuẩn dựa vào từ khóa người dùng nhập.
- **Hiển thị đồ thị tương tác 2D:** Đồ thị trực quan, hỗ trợ kéo thả (drag), phóng to thu nhỏ (zoom & pan), và click vào node để xem chi tiết.
- **Tiến độ thời gian thực (Real-time Progress):** Thanh Overlay hiển thị log hoạt động (đang truy vấn node nào, độ sâu bao nhiêu) không gây cảm giác bị treo cho người dùng.
- **Cơ chế Caching mạnh mẽ:** Tích hợp Redis giúp hệ thống không phải tính toán lại những truy vấn đã từng thực hiện, tránh vượt quá giới hạn API (Rate limit) của Wikidata.
- **Giao diện tối (Dark Mode):** Thiết kế hiện đại, mượt mà và trực quan.

---

## 4. Input & Output (IO)

### **Input**
- **Tham số tìm kiếm:** `start_entity` (Wikidata ID, VD: Q123) và `end_entity` (Wikidata ID, VD: Q456).
- Tương tác của người dùng trên Web UI.

### **Output**
- **Progress Stream:** Các chuỗi JSON thông báo tiến trình qua SSE (ví dụ: `{"type": "progress", "visited": 1500, "depth": 2}`).
- **Graph Data (Kết quả):** Một đối tượng JSON chứa:
  - `nodes`: Danh sách các điểm (chứa ID, tên, mô tả, ảnh đại diện).
  - `links`: Danh sách các đường nối (chứa `source`, `target` và `label` là loại quan hệ - VD: "nơi sinh", "làm việc cho").
- **UI:** Hình ảnh đồ thị mạng lưới liên kết trực quan.

---

## 5. Chi Tiết Kết Nối API & Tích Hợp (API Connections & Integrations)

Hệ thống hoạt động dựa trên hai tập hợp API chính: Internal API (giữa Frontend và Backend) và External API (giữa Backend và Wikidata). Đi kèm là các thông số kỹ thuật và cấu hình sâu ở mức code.

### 5.1. Internal APIs (Frontend kết nối Backend)
Các API này được host bởi FastAPI tại `/api` và giao tiếp qua HTTP/REST hoặc luồng Server-Sent Events (SSE).

- **`GET /api/search`**: Endpoint tìm đường nối nguyên khối, trả về JSON toàn bộ path hoặc mảng rỗng nếu không có. Hỗ trợ cấu hình mức độ quét sâu qua query param `mode`:
  - **`fast` mode**: 
    - Tham số `max_depth` thực tế bị giới hạn (cap) ở mức 6.
    - Giới hạn query SPARQL lấy láng giềng: 20 nodes/truy vấn.
    - Max memory nodes (giới hạn an toàn BFS mở rộng): 6.000 nodes.
    - Timeout cho mỗi truy vấn SPARQL: 6 giây.
  - **`deep` mode**: Dùng khi `fast` thất bại và cần càn quét sâu.
    - Tham số `max_depth` mở ra lên tới tối đa 10.
    - Giới hạn query SPARQL lấy láng giềng: nới rộng lên 50 nodes/truy vấn.
    - Max memory nodes: mở rộng tới 15.000 nodes. Backend sẽ ép (force) thuật toán ngừng quét nếu vượt quá số này để tránh OOM (Out Of Memory).
    - Timeout cho mỗi lệnh SPARQL: 12 giây.

- **`GET /api/search/stream`**: Endpoint quan trọng nhất sử dụng cơ chế Server-Sent Events (`sse-starlette`). 
  - Trong quá trình quét đồ thị sử dụng cấu trúc **Bi-directional BFS (Tìm kiếm theo chiều rộng 2 chiều)** từ hai đầu, backend liên tục `yield` gói tin JSON thời gian thực về frontend: `{"event": "progress", "data": {"node_id": "...", "total_explored": 120, "current_depth": 2, "elapsed_seconds": 1.5}}`. Frontend nhận và vẽ log ngay lập tức.
  - Khi hoàn tất luồng BFS, gửi event `complete` kèm mảng dữ liệu path JSON, hoặc event `error` nếu rớt mạng.

- **`GET /api/suggestions?q={text}&limit={n}`**: API Auto-complete tên sang QID. Gộp dữ liệu từ lịch sử tìm kiếm cục bộ (history in Redis) và lệnh search Action API lên Wikidata. Output Format JSON: `[{"qid": "...", "label": "...", "description": "...", "source": "history|wikidata"}]`.

- **`GET /api/history`**: Kéo lịch sử tìm kiếm (global history). Dữ liệu là JSON mảng giới hạn cứng bằng Redis lệnh `LTRIM` để chỉ giữ đúng 20 cặp đôi đã tìm kiếm gần nhất.

- **`GET /api/neighbors/{wikidata_id}`**: Lấy danh sách thô tất cả neighbor của một node (Dùng chủ yếu cho test/debug nội bộ).

### 5.2. External APIs (Backend kết nối Wikidata)
Backend đóng vai trò là một Agent Client truy xuất trực tiếp dữ liệu thô từ hạ tầng server Wikipedia:

- **Wikidata SPARQL Endpoint** (`https://query.wikidata.org/sparql`): 
  - Backend bắn câu truy vấn SPARQL ở tần suất cao qua script `neighbor_wikidata.py`. 
  - Query được tối ưu tối đa bằng toán tử `UNION`: Quét song song trường hợp Node hiện tại đóng vai trò là Chủ thể (`wd:QID ?p ?neighbor`) HOẶC Tân ngữ (`?neighbor ?p wd:QID`).
  - Code sử dụng string manipulation: `FILTER(STRSTARTS(STR(?neighbor), "http://www.wikidata.org/entity/Q"))` để "ép" kết quả trả về chỉ là QID (những thực thể chuẩn, loại bỏ các kết nối rác như file hình ảnh, link ngoài, năm sinh dạng chuỗi).

- **Wikidata Action API** (`wbsearchentities` / `wbgetentities`): Giao tiếp qua HTTP REST (sử dụng thư viện `requests` trong `wikidata_client.py`) phục vụ việc dịch văn bản người dùng gõ (ví dụ "Harry Potter") sang ID Wikidata ("Q8337") kèm theo description.

### 5.3. External Tools & Caching Architecture
- **Redis In-Memory Database**: "Trái tim" bộ nhớ đệm chạy tại port 6379, được gọi thông qua package `redis-py` trong `redis.py`:
  - **Neighbors Cache:** Node láng giềng được lưu cache tại Key format `neighbors:{wikidata_id}:{limit}` với TTL sống 48 tiếng (172800s). Giúp giải quyết triệt để lỗi chặn Rate Limit 429 từ Wikidata API khi BFS mở rộng hàng ngàn node.
  - **Path Cache:** Lộ trình đường đi (short-path) được lưu tại Key format `path:{start}:{target}:{mode}:{depth}` với TTL 24 tiếng (86400s).
  - **LIFO History Queue:** Danh sách tìm kiếm lưu tại key `global_history` dưới cấu trúc mảng (`lrange 0 -1`), mỗi lần có thêm dữ liệu nó sẽ được chèn bằng `LPUSH` và cắt rác bằng `LTRIM 0 19`.
  - *Cơ chế Fallback*: Khi Redis offline hay restart, các hàm cache trong `redis.py` được bọc try-except tự động bắt `ConnectionError` và fallback thẳng về sử dụng biến in-memory dictionary gốc của Python (`_memory_cache`), đảm bảo ứng dụng không chết.
- **react-force-graph-2d / d3-force**: Thư viện đồ họa cốt lõi phía Client. Tự động dàn trang Node nhờ một hệ thống "thuật toán mô phỏng vật lý" mạnh mẽ (Mô phỏng 2 lực: lực đẩy từ trường (repulsion) giữa các Node và lực đàn hồi lò xo (spring) kéo giãn các đường Links) khiến cho đồ họa 2D hiển thị tự do bay lơ lửng và luôn đạt trạng thái cân bằng.

---

## 6. Thư Viện & Công Nghệ Sử Dụng (Technologies Stack)

### **Frontend:**
- **React (v19) & Vite:** Xây dựng giao diện người dùng và build project siêu tốc.
- **react-force-graph-2d & d3:** Dựng và xử lý đồ thị network dạng physics-based 2D.
- **lucide-react:** Sử dụng bộ icon.
- **axios:** Giao tiếp với HTTP Backend API.
- **CSS thuần / UI UX:** Xử lý Dark mode và animation.

### **Backend:**
- **Python (3.9+):** Ngôn ngữ chính xử lý logic.
- **FastAPI & Uvicorn:** Framework Web hiệu năng cực cao, hỗ trợ tốt luồng bất đồng bộ (async).
- **sse-starlette:** Thư viện hỗ trợ truyền phát Server-Sent Events cho việc cập nhật realtime progress.
- **Requests:** Thư viện gọi HTTP request (thường là gọi Wikidata SPARQL endpoint).
- **Pydantic:** Xác thực dữ liệu đầu vào và config environments.
- **Redis (redis-py):** Tương tác với cơ sở dữ liệu in-memory Redis.

### **Hạ tầng & Nguồn Dữ Liệu:**
- **Docker & Docker Compose:** Container hóa các dịch vụ để có thể chạy dễ dàng bằng một lệnh (Frontend, Backend, Redis database).
- **Wikidata API & SPARQL:** Nguồn dữ liệu tri thức khổng lồ mở.

---

## 7. Cấu Trúc File & Folder Chi Tiết

Dưới đây là cấu trúc cây thư mục phản ánh rõ kiến trúc Client-Server của dự án:

```text
name-related-searching/
├── docker-compose.yml          # Tệp cấu hình chạy đồng thời Frontend, Backend và Redis bằng Docker
├── README.md                   # Tài liệu hướng dẫn cài đặt và thông tin tóm tắt dự án
├── docs/                       # Thư mục chứa tài liệu mô tả hệ thống (Markdown)
├── overall.md                  # Tài liệu tổng quan kiến trúc (File này)
└── src/                        # Thư mục gốc chứa Source Code của hệ thống
    │
    ├── frontend/               # MÃ NGUỒN FRONTEND (Web Client)
    │   ├── package.json        # Chứa thông tin cấu hình npm, dependencies của React
    │   ├── vite.config.js      # Cấu hình đóng gói cho Vite
    │   ├── index.html          # Điểm vào HTML gốc của ứng dụng
    │   └── src/                # Logic code Frontend
    │       ├── main.jsx        # Điểm vào (Entry point) khởi tạo root của React
    │       ├── App.jsx         # Component gốc chứa layout, quản lý trạng thái search và xử lý logic kết nối
    │       ├── App.css         # Các styles CSS riêng cho layout chính
    │       ├── index.css       # Các styles CSS toàn cục (variables, dark mode)
    │       ├── components/     # Các UI Component độc lập, tái sử dụng được
    │       │   ├── Graph.jsx           # Bao bọc `react-force-graph-2d` để vẽ cấu trúc các nodes & links
    │       │   └── ProgressOverlay.jsx # Component hiển thị panel log & progress bar trong lúc thuật toán chạy
    │       ├── lib/            # Tiện ích bổ sung (utilities)
    │       └── assets/         # Tài nguyên tĩnh (icons, hình ảnh minh họa)
    │
    └── backend/                # MÃ NGUỒN BACKEND (FastAPI API)
        ├── requirements.txt    # Danh sách các thư viện Python (FastAPI, Redis, sse-starlette,...)
        ├── Dockerfile          # Tệp định nghĩa môi trường image Docker cho Backend
        └── app/                # Package gốc của API
            ├── main.py         # Entry point API: Khởi tạo FastAPI app, cấu hình CORS, kết nối routes
            │
            ├── core/           # Cấu hình Cốt lõi của hệ thống
            │   ├── config.py   # Quản lý các biến môi trường (Pydantic Settings)
            │   └── redis.py    # Quản lý Connection Pool đến cơ sở dữ liệu Redis
            │
            ├── api/            # Định nghĩa các Controller / Endpoint
            │   └── routes.py   # Nhận các HTTP Request (`/api/suggest`, `/api/search/...`)
            │
            └── services/       # Lớp Business Logic (Nghiệp vụ cốt lõi)
                ├── bfs_service.py       # Cài đặt thuật toán duyệt đồ thị BFS trên tập data Wikidata
                ├── path_service.py      # Điều phối xử lý pathfinding (gọi cache, chạy bfs, gửi sse stream)
                ├── neighbor_wikidata.py # Xây dựng & gửi câu lệnh truy vấn SPARQL lên hệ thống máy chủ Wikidata
                ├── suggestion_service.py# Giao tiếp với hệ thống Search Wikidata để gợi ý ID cho người dùng
                ├── normalize.py         # Chuyển đổi dữ liệu thô SPARQL về định dạng chuẩn Graph (Nodes, Links)
                ├── file_cache.py        # Module quản lý cache dựa vào file (Fallback khi mất kết nối Redis)
                ├── input_utils.py       # Module kiểm tra định dạng và trích xuất (parse) đầu vào của user
                └── graph_config.py      # Định nghĩa các hằng số, filter property bỏ qua cho đồ thị
```
