# Tổng Quan Dự Án: WikiBFS (Name Related Searching)

## 1. Tổng Quan (Overview)
**WikiBFS** là một ứng dụng web cho phép người dùng tìm kiếm, khám phá và hiển thị trực quan đường nối ngắn nhất giữa hai thực thể bất kỳ trên Wikidata (ví dụ: người, tổ chức, địa danh, tác phẩm, v.v.). 
Hệ thống sử dụng thuật toán **Breadth-First Search (BFS) Hai Chiều Bất Đồng Bộ** để duyệt nhanh chóng qua mạng lưới đồ thị khổng lồ của Wikidata. Dự án thiết kế theo kiến trúc Client-Server hiện đại:
*   **Frontend**: React (v19) & Vite, sử dụng `react-force-graph-2d` hiển thị đồ thị tương tác dạng hạt kết hợp phong cách thiết kế **2D Retro Game (Light Theme)** độc đáo, thân thiện, trực quan. Giao diện được bản địa hóa 100% bằng **Tiếng Anh** để hướng tới người dùng toàn cầu.
*   **Backend**: FastAPI & Uvicorn, xử lý luồng sự kiện thời gian thực thông qua Server-Sent Events (SSE), tích hợp hệ thống bộ nhớ đệm **Redis Caching** hai chiều giúp giảm thiểu tối đa giới hạn truy vấn (Rate Limits/HTTP 429) và lỗi quá thời gian kết nối (Timeouts/HTTP 504) từ hệ thống Wikidata SPARQL.

---

## 2. Luồng Hoạt Động (Flow)
Luồng xử lý từ lúc nhập liệu đến khi hiển thị kết quả diễn ra như sau:

1.  **Autocomplete & Gợi ý (Suggestions)**: Người dùng nhập tên thực thể. Frontend gọi API `/api/suggestions` gửi truy vấn Wikidata Action API (được tối ưu kết hợp với từ khóa lịch sử trong Redis) để tìm QID tương ứng (ví dụ: `Q34660` cho J.K. Rowling).
2.  **Kích hoạt tìm kiếm (SSE Stream)**: Khi người dùng bấm nút **FIND PATH**, ứng dụng gửi kết nối SSE dạng dài tới `/api/search/stream`.
3.  **Kiểm tra Cache & Hubs**:
    *   Backend kiểm tra Redis Cache xem cặp đôi tìm kiếm đã được giải quyết chưa. Cổng kết nối Redis `6379` được ánh xạ ra host máy vật lý để tiến trình dev uvicorn có thể tận dụng in-memory database tốc độ cao.
    *   **Pre-fetch Hubs**: Worker chạy nền đồng bộ trước láng giềng của các thực thể chiến lược siêu kết nối (`Q5`, `Q30`, v.v.) vào Redis.
    *   **Phân trang lịch sử**: Lịch sử tìm kiếm toàn cục (`/api/history`) được phân trang động tối ưu bằng `LLEN` và `LRANGE` để đảm bảo tốc độ phản hồi O(1).
4.  **Duyệt đồ thị bất đồng bộ**: Nếu chưa có cache, `bfs_service.py` thực hiện tìm kiếm A* / BFS hai chiều trên luồng bất đồng bộ. Các truy vấn SPARQL Wikidata được đẩy qua `asyncio.to_thread` để tránh block Event Loop.
5.  **Dọn dẹp tài nguyên tự động**: Khi người dùng ngắt kết nối giữa chừng, FastAPI ném ra `GeneratorExit`. Tầng Route phát hiện và kích hoạt khối `finally` dọn dẹp hàng đợi lập tức để chống rò rỉ bộ nhớ (SSE leaks).
6.  **Tối giản hóa đồ thị (Minimization)**: Khi tìm thấy đường đi, backend chạy `minimize_graph_payload` rút gọn dữ liệu thô thành đồ thị phẳng mỏng nhẹ (chỉ giữ `nodes` và `links` chứa nhãn quan hệ).
7.  **Giải phân giải Wikipedia Sitelinks**: Hệ thống phân tích Wikidata `sitelinks` để xác định bài viết tương ứng trên Wikipedia:
    *   Ưu tiên bài viết **Wikipedia Tiếng Việt** (`viwiki`).
    *   Nếu không có, ưu tiên bài viết **Wikipedia Tiếng Anh** (`enwiki`).
    *   Nếu không có bài viết nào, sẽ fallback về trang thông tin thực thể **Wikidata** (`https://www.wikidata.org/wiki/...`).
8.  **Hiển thị (UI Rendering)**: Frontend nhận gói tin `complete`, dựng đồ thị physics-based mượt mà. Đồng thời thanh kết quả dưới chân màn hình (`bottom bar`) chuyển đổi từ QID thô sang hiển thị tên thực thể rõ ràng (ví dụ: "Jack Sparrow"), đóng vai trò là các nút bấm liên kết trực tiếp tới trang Wikipedia tương ứng, được trang trí theo phong cách 2D Retro viền đen dày nổi bật.

---

## 3. Chức Năng (Functions & Features)
*   **Tìm kiếm BFS hai chiều bất đồng bộ**: Tiết kiệm tài nguyên quét đồ thị $O(b^{d/2})$ so với $O(b^d)$ của BFS thông thường.
*   **Tiến độ thời gian thực (Real-time Progress)**: Hiển thị trạng thái các node đang quét, chiều sâu hiện tại thông qua luồng SSE dài.
*   **Bản dịch Wikipedia thông minh**: Tự động chuyển đổi QID thành đường link Wikipedia đa ngôn ngữ.
*   **2D Retro Game (Light Theme) UI**: Giao diện sáng sủa độc đáo lấy tông trắng ấm `#fafaf9` và màu vàng sáng `#facc15` làm điểm nhấn, phối cùng nét chữ tròn trịa `Poppins`, viền đen nổi bật đậm chất hoạt hình.
*   **Thanh Sidebar trượt thu gọn (Dock + Sliding Panel)**:
    *   **Left Dock** cố định bên trái (64px) chứa logo vàng tươi và các nút tab chuyển hướng.
    *   **Sliding Panel** bên cạnh (280px) trượt ẩn hoàn toàn phía sau Dock khi không sử dụng để mở rộng tối đa 100% diện tích màn hình cho đồ thị.
*   **Tải lại lịch sử thông minh (History Replay)**: Bấm vào phần tử lịch sử trong sidebar sẽ tái hiện lại ngay tức thì đồ thị tương tác từ dữ liệu cache đã lưu sẵn mà không cần tính toán lại từ đầu.

---

## 4. Input & Output (IO)

### **Input**
*   `start_entity` (Wikidata ID, VD: Q34660 hoặc từ khóa tên) và `target_entity` (Wikidata ID, VD: Q173746).
*   Thao tác điều hướng: Zoom, kéo thả node, chuyển tab sidebar, xem lại lịch sử.

### **Output**
*   **Progress Stream**: Chuỗi JSON tiến trình thực tế (`{"node_id": "...", "total_explored": 120, "current_depth": 2}`).
*   **Graph Data**: Khối JSON tinh gọn chứa danh sách `nodes` (id, tên hiển thị) và `links` (source, target, nhãn liên kết quan hệ).
*   **UI**: Đồ thị physics tương tác mượt mà và thanh điều hướng đường đi chi tiết dẫn liên kết đến Wikipedia.

---

## 5. Chi Tiết Kết Nối API & Tích Hợp (API Connections & Integrations)

### 5.1. Internal APIs (Frontend kết nối Backend)
Host bởi FastAPI tại `/api`:
*   **`GET /api/search`**: Endpoint tìm kiếm đồng bộ cơ bản.
*   **`GET /api/search/stream`**: Truyền phát Server-Sent Events qua `find_path` async generator. Hỗ trợ 2 chế độ:
    *   `fast` mode: Max depth 6, giới hạn bộ nhớ 6,000 nodes, timeout 6 giây.
    *   `deep` mode: Max depth 10, giới hạn bộ nhớ 15,000 nodes, timeout 12 giây.
*   **`GET /api/suggestions?q={text}&limit={n}`**: Tự động gợi ý thực thể dựa trên Action API của Wikidata và lịch sử đệm Redis.
*   **`GET /api/history`**: Kéo lịch sử toàn cục có áp dụng phân trang LIFO từ Redis Cache (`LLEN` / `LRANGE`).

### 5.2. External APIs (Backend kết nối Wikidata)
*   **Wikidata SPARQL Endpoint** (`https://query.wikidata.org/sparql`):
    *   Truy vấn song song 2 chiều (Chủ thể/Tân ngữ) qua liên kết `UNION`.
    *   Tối ưu hóa bộ lọc RDF index bằng **`FILTER(isURI(?neighbor))`** thay thế cho `STRSTARTS` để tăng tốc độ phản hồi 15% - 40%.
*   **Wikidata Action API** (`wbsearchentities` / `wbgetentities`): Tìm kiếm tên thực thể và phân giải nhãn, sitelinks của Wikipedia.

---

## 6. Thuật Toán Tìm Kiếm Cốt Lõi (Async Bi-directional BFS)
Triển khai trong `bfs_service.py` giúp hạn chế sự bùng nổ tổ hợp của đồ thị:
1.  **Hai hàng đợi song hành**: `forward_queue` (từ Start) và `backward_queue` (từ Target).
2.  **Cân bằng hàng đợi**: Ưu tiên bốc và mở rộng nhánh hàng đợi có kích thước nhỏ hơn để cân bằng năng lượng xử lý.
3.  **Hội ngộ điểm giữa**: Khi một node lân cận ở nhánh này đã được duyệt và lưu vết bởi nhánh đối diện, đường đi hoàn chỉnh được phục dựng ngay tức khắc.
4.  **Failsafes phòng vệ**: Kiểm soát chặt chẽ giới hạn thời gian thực tế và lượng node nạp vào bộ nhớ để chống tràn RAM.

---

## 7. Cấu Trúc File & Folder Chi Tiết
```text
name-related-searching/
├── docker-compose.yml          # Container hóa đồng bộ các thành phần (Frontend, Backend, Redis, Nginx)
├── README.md                   # Hướng dẫn cài đặt dự án
├── docker/
│   └── nginx/
│       └── nginx.conf          # Gateway quản lý SSE và SPA routing
├── docs/
│   └── overall/
│       ├── overall.md          # Tài liệu tổng quan kiến trúc (File này)
│       └── project_assessment.md # Báo cáo đánh giá hiệu năng dự án
├── src/
    ├── frontend/               # MÃ NGUỒN FRONTEND
    │   ├── index.html          # File HTML gốc (nạp phông Poppins và favicon vàng)
    │   └── src/
    │       ├── App.jsx         # Layout chính (Dock + Panel, luồng xử lý SSE)
    │       ├── App.css         # Thiết kế 2D Retro Game (Light Theme)
    │       ├── components/
    │       │   ├── Graph.jsx           # Dựng đồ thị ForceGraph2D viền node đen sắc nét
    │       │   └── ProgressOverlay.jsx # Panel tiến trình tìm kiếm thời gian thực
    │       └── public/
    │           └── favicon.svg         # SVG favicon thương hiệu màu vàng tươi
    └── backend/                # MÃ NGUỒN BACKEND
        └── app/
            ├── main.py         # Điểm vào ứng dụng FastAPI
            ├── core/
            │   └── redis.py    # Quản lý in-memory Redis database & pagination logic
            └── services/
                ├── bfs_service.py       # Thuật toán Bi-directional BFS bất đồng bộ
                ├── path_service.py      # Bộ điều phối luồng tìm kiếm
                └── neighbor_wikidata.py # Tạo và bắn truy vấn SPARQL tối ưu hóa
```
