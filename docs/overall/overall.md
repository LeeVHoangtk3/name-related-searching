# Tổng Quan Dự Án: WikiBFS (Name Related Searching)

## 1. Tổng Quan (Overview)
**WikiBFS** là một ứng dụng web cho phép người dùng tìm kiếm, khám phá và hiển thị đường nối ngắn nhất giữa hai thực thể bất kỳ trên Wikidata (ví dụ: người, tổ chức, sự kiện, v.v.). 
Hệ thống sử dụng thuật toán **Breadth-First Search (BFS)** để duyệt qua mạng lưới đồ thị khổng lồ của Wikidata, tìm ra các mối quan hệ liên kết chúng. Dự án được thiết kế với kiến trúc Client-Server (Frontend React và Backend FastAPI), cho phép tương tác thời gian thực thông qua Server-Sent Events (SSE) và tối ưu hóa tốc độ truy xuất bằng Redis cache.

---

## 2. Luồng Hoạt Động (Flow)
Luồng xử lý từ lúc người dùng nhập thông tin đến khi hiển thị kết quả diễn ra như sau:

1. **Gợi ý & Nhập liệu (Input):** Người dùng nhập tên của thực thể bắt đầu và thực thể kết thúc. Frontend sẽ gọi API `/api/suggest` (thông qua `suggestion_service.py`) tới Wikidata để tự động hiển thị gợi ý và map tên văn bản thành **Wikidata ID** (VD: `Q34660`).
2. **Kích hoạt tìm kiếm:** Khi nhấn "Tìm kiếm", Frontend sẽ mở một kết nối **Server-Sent Events (SSE)** tới Backend (`/api/search/...`).
3. **Kiểm tra Cache & Pre-fetch Hubs:** Backend nhận ID, trước tiên kiểm tra trong **Redis Cache** (hoặc `file_cache.py`) xem đường đi đã được tính toán chưa.
   - **Đồng bộ Hubs chạy nền**: Khi khởi động Backend, worker chạy nền (`sync_hubs_cache_worker` thông qua lifespan của FastAPI) sẽ tải trước (Pre-fetch) láng giềng của các thực thể chiến lược lớn (`Q5`, `Q30`, `Q571`, `Q11424`, `Q4830453`) và nạp vào Redis (`hub_cache:QID`). Khi BFS mở rộng qua các Hub này, dữ liệu láng giềng được trả về ngay trong `<5ms` thay vì gửi truy vấn mạng SPARQL, giúp tránh lỗi rate-limit (HTTP 429) và timeout (HTTP 504) của Wikidata.
   - **Phân trang lịch sử**: Bản ghi lịch sử tìm kiếm được lấy qua endpoint `/api/history` áp dụng phân trang động bằng lệnh `LLEN` và `LRANGE` của Redis để tối ưu băng thông.
4. **Thực thi BFS Bất Đồng Bộ (Xử lý Đồ thị):** Nếu chưa có cache, `path_service.py` hoặc `routes.py` sẽ khởi chạy thuật toán BFS bất đồng bộ (`find_path` async generator) qua `bfs_service.py`. 
   - Hệ thống liên tục gửi các truy vấn SPARQL (`neighbor_wikidata.py`) để lấy tất cả các láng giềng (neighbor) của các node ở độ sâu hiện tại, thực hiện qua `asyncio.to_thread` để không chặn Event Loop.
   - Trong quá trình này, backend liên tục `yield` (đẩy) tiến trình (Progress) về Frontend thông qua SSE để người dùng biết thuật toán đang quét bao nhiêu node.
   - Khi client ngắt kết nối giữa chừng, FastAPI phát hiện qua `request.is_disconnected()` và đóng generator BFS (`bfs_gen.aclose()`), kích hoạt khối `finally` dọn dẹp các hàng đợi lập tức để chống rò rỉ tài nguyên.
5. **Rút Gọn Payload & Lưu Cache:** Khi tìm được đường đi ngắn nhất, dữ liệu thô sẽ được đưa qua hàm `minimize_graph_payload` trong `normalize.py` để chỉ giữ lại các trường tối giản cho đồ thị phẳng (`nodes` chứa `id`/`name` và `links` chứa `source`/`target`/`p_label`). Kết quả này được lưu vào Redis để dùng cho lần sau.
6. **Render Giao Diện (Output):** Frontend nhận dữ liệu JSON hoàn chỉnh đã được phân giải sẵn nhãn thực thể và quan hệ, sử dụng component `Graph.jsx` (thư viện `react-force-graph-2d`) để vẽ đồ họa 2D minh họa cho đường đi này cực kỳ mượt mà.

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
  - Khởi tạo và lặp bất đồng bộ qua async generator `find_path(...)`. Trong quá trình quét đồ thị sử dụng cấu trúc **Bi-directional BFS (Tìm kiếm theo chiều rộng 2 chiều)** từ hai đầu, backend liên tục `yield` gói tin JSON tiến độ thời gian thực về frontend.
  - Khi hoàn tất, backend tự động gọi `minimize_graph_payload(...)` để thu gọn cấu trúc phẳng (`nodes` gồm `id` và `name`, `links` gồm `source`, `target` và `p_label`) gửi qua event `complete` để frontend chỉ việc vẽ mà không cần tự gọi thêm API Wikidata để phân giải nhãn thực thể.
  - Kiểm soát kết nối mạng thực tế qua `await request.is_disconnected()`. Nếu client disconnect, generator tự động dừng và đóng generator BFS (`bfs_gen.aclose()`), kích hoạt khối `finally` dọn dẹp các queue để chống rò rỉ bộ nhớ.

- **`GET /api/suggestions?q={text}&limit={n}`**: API Auto-complete tên sang QID. Gộp dữ liệu từ lịch sử tìm kiếm cục bộ (history in Redis) và lệnh search Action API lên Wikidata. Output Format JSON: `[{"qid": "...", "label": "...", "description": "...", "source": "history|wikidata"}]`.

- **`GET /api/history`**: Kéo lịch sử tìm kiếm (global history). Dữ liệu là JSON mảng giới hạn cứng bằng Redis lệnh `LTRIM` để chỉ giữ đúng 20 cặp đôi đã tìm kiếm gần nhất.

- **`GET /api/neighbors/{wikidata_id}`**: Lấy danh sách thô tất cả neighbor của một node (Dùng chủ yếu cho test/debug nội bộ).

### 5.2. External APIs (Backend kết nối Wikidata)
Backend đóng vai trò là một Agent Client truy xuất trực tiếp dữ liệu thô từ hạ tầng server Wikipedia:

- **Wikidata SPARQL Endpoint** (`https://query.wikidata.org/sparql`): 
  - Backend bắn câu truy vấn SPARQL ở tần suất cao qua script `neighbor_wikidata.py`. 
  - Query được tối ưu tối đa bằng toán tử `UNION`: Quét song song trường hợp Node hiện tại đóng vai trò là Chủ thể (`wd:QID ?p ?neighbor`) HOẶC Tân ngữ (`?neighbor ?p wd:QID`).
  - Sử dụng bộ lọc tối ưu hóa RDF Index: `FILTER(isURI(?neighbor))` thay thế cho bộ lọc chuỗi cũ `STRSTARTS` nhằm tăng tốc độ truy vấn, giảm nguy cơ dính lỗi HTTP 429 và Timeout.

- **Wikidata Action API** (`wbsearchentities` / `wbgetentities`): Giao tiếp qua HTTP REST (sử dụng thư viện `requests` trong `wikidata_client.py`) phục vụ việc dịch văn bản người dùng gõ sang ID Wikidata kèm theo description.

### 5.3. External Tools & Caching Architecture
- **Redis In-Memory Database**: "Trái tim" bộ nhớ đệm chạy tại port 6379, được gọi thông qua package `redis-py` trong `redis.py`.
- **Nginx Reverse Proxy**: Đứng trước backend để quản lý SSL/TLS termination, cân bằng tải (load balancing) cho các luồng SSE dài, và chặn các request bất thường từ client.

---

## 6. Thuật Toán Tìm Kiếm Cốt Lõi (Async Bi-directional BFS)

Trái tim của hệ thống là thuật toán **Tìm kiếm theo chiều rộng 2 chiều bất đồng bộ (Async Bi-directional Breadth-First Search)** được triển khai chặt chẽ trong `bfs_service.py`. Tại sao không dùng BFS 1 chiều thông thường? Vì đồ thị Wikidata là một mạng lưới khổng lồ (với hàng chục triệu node và tỷ cạnh), việc quét 1 chiều từ A -> B sẽ tạo ra sự bùng nổ tổ hợp (combinatorial explosion) dẫn đến quá tải bộ nhớ rất nhanh.

Cơ chế hoạt động chi tiết của thuật toán:
1. **Khởi tạo 2 hàng đợi (Queues):** `forward_queue` bắt đầu từ `start_id` và `backward_queue` bắt đầu từ `target_id` (sử dụng `collections.deque` để tối ưu O(1) thao tác popleft). Đi kèm là 2 từ điển (dictionary) để lưu vết đường đi (`forward_parent`, `backward_parent`) và lưu độ sâu (`forward_depth`, `backward_depth`).
2. **Chiến lược Cân Bằng (Load-balancing):** Ở mỗi vòng lặp `while`, hệ thống kiểm tra và so sánh kích thước của 2 hàng đợi. Nó luôn chọn **hàng đợi có ít node hơn** (`len(forward_queue) <= len(backward_queue)`) để mở rộng (expand). Việc này đảm bảo thuật toán luôn ưu tiên phát triển nhánh đồ thị thưa thớt hơn, tiết kiệm tài nguyên và số lượng lệnh gọi API tối đa.
3. **Mở rộng theo lớp & Yield Progress:** Hàm `expand_one_layer` được định nghĩa là một sub-generator async. Khi duyệt qua mỗi node được bốc ra (`queue.popleft()`), hệ thống sẽ `yield` tiến độ và gọi `asyncio.to_thread(get_neighbors, current)` chạy query Wikidata SPARQL trong thread pool để tránh block Event Loop.
4. **Cơ chế Hội Ngộ (Meeting Point):** Nếu một node láng giềng vừa tìm được ở nhánh này đã nằm sẵn trong `parent_dict` của nhánh bên kia (nghĩa là `neighbor in other_parent`), và tổng độ sâu (`depth + other_depth`) nhỏ hơn hoặc bằng `max_depth` cho phép, thì hệ thống xác định **Điểm Hội Ngộ** đã được tìm thấy và lập tức trả kết quả.
5. **Dựng lại đường đi (Path Reconstruction):** Hàm nội bộ `_build_path` sẽ đi ngược (gỡ băng) từ điểm hội ngộ về điểm xuất phát thông qua `forward_parent` và từ điểm hội ngộ về đích thông qua `backward_parent`. Cả 2 mảng được ghép lại tạo thành chuỗi liên kết hoàn chỉnh từ đầu đến cuối.
6. **Hủy Bỏ An Toàn (Finally Garbage Collection):** Bọc toàn bộ thuật toán trong khối `try ... finally`. Khi generator bị đóng bằng `.aclose()` do client ngắt kết nối (FastAPI kích hoạt `GeneratorExit`), khối `finally` sẽ luôn chạy và gọi `clear()` trên toàn bộ queues và parent maps, giải phóng bộ nhớ RAM lập tức để chống OOM.
7. **Failsafes (Bảo vệ Server):** Hàm `enforce_limits()` chèn ở khắp mọi nơi trong thân vòng lặp, có nhiệm vụ "bóp cò" chặn đứng quá trình quét ném ra Exception `SearchLimitReached` nếu tổng số node mở rộng đã chạm trần hoặc tổng thời gian chạy đã vượt quá ngưỡng cho phép.

---

## 7. Thư Viện & Công Nghệ Sử Dụng (Technologies Stack)

### **Frontend:**
- **React (v19) & Vite:** Xây dựng giao diện người dùng và build project siêu tốc.
- **react-force-graph-2d & d3:** Dựng và xử lý đồ thị network dạng physics-based 2D.
- **lucide-react:** Sử dụng bộ icon.
- **axios:** Giao tiếp với HTTP Backend API.
- **CSS thuần / UI UX:** Xử lý Dark mode và animation.

### **Backend:**
- **Python (3.11+):** Ngôn ngữ chính xử lý logic.
- **FastAPI & Uvicorn:** Framework Web hiệu năng cực cao, hỗ trợ tốt luồng bất đồng bộ (async).
- **sse-starlette:** Thư viện hỗ trợ truyền phát Server-Sent Events cho việc cập nhật realtime progress.
- **Requests:** Thư viện gọi HTTP request (thường là gọi Wikidata SPARQL endpoint).
- **Pydantic:** Xác thực dữ liệu đầu vào và config environments.
- **Redis (redis-py):** Tương tác với cơ sở dữ liệu in-memory Redis.

### **Hạ tầng & Nguồn Dữ Liệu:**
- **Docker & Docker Compose:** Container hóa các dịch vụ để có thể chạy dễ dàng bằng một lệnh (Frontend, Backend, Redis database) thông qua Nginx Reverse Proxy.
- **Wikidata API & SPARQL:** Nguồn dữ liệu tri thức khổng lồ mở.

---

## 8. Cấu Trúc File & Folder Chi Tiết

Dưới đây là cấu trúc cây thư mục phản ánh rõ kiến trúc Client-Server của dự án:

```text
name-related-searching/
├── docker-compose.yml          # Tệp cấu hình chạy đồng thời các container (Frontend, Backend, Redis, Nginx)
├── README.md                   # Tài liệu hướng dẫn cài đặt và thông tin tóm tắt dự án
├── docker/                     # Thư mục cấu hình hạ tầng Production
│   └── nginx/
│       └── nginx.conf          # Cấu hình Nginx Gateway (SSE, SPA Routing, API Reverse Proxy)
├── docs/                       # Thư mục chứa tài liệu mô tả hệ thống (Markdown)
│   └── overall/                # Thư mục tài liệu tổng quan
│       ├── overall.md          # Tài liệu tổng quan kiến trúc (File này)
│       └── project_assessment.md # Tài liệu đánh giá dự án chuyên sâu
├── scripts/                    # Thư mục chứa các kịch bản kiểm thử, vận hành tự động
│   └── validation/             # Bộ kịch bản xác minh hệ thống tự động
│       ├── windows/            # Các script PowerShell dành cho Windows Host
│       └── docker/             # Các script Bash dành cho Docker/Linux
└── src/                        # Thư mục gốc chứa Source Code của hệ thống
    │
    ├── frontend/               # MÃ NGUỒN FRONTEND (Web Client)
    │   ├── package.json        # Chứa thông tin cấu hình npm, dependencies của React
    │   ├── vite.config.js      # Cấu hình đóng gói cho Vite
    │   ├── index.html          # Điểm vào HTML gốc của ứng dụng
    │   ├── nginx.conf          # Cấu hình Nginx tối ưu phục vụ React tĩnh
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
                ├── cache_syncer.py      # Worker chạy nền đồng bộ trước cache láng giềng của các Wikidata Hubs chiến lược
                ├── suggestion_service.py# Giao tiếp với hệ thống Search Wikidata để gợi ý ID cho người dùng
                ├── normalize.py         # Chuyển đổi dữ liệu thô SPARQL về định dạng chuẩn Graph (Nodes, Links)
                ├── file_cache.py        # Module quản lý cache dựa vào file (Fallback khi mất kết nối Redis)
                ├── input_utils.py       # Module kiểm tra định dạng và trích xuất (parse) đầu vào của user
                └── graph_config.py      # Định nghĩa các hằng số, filter property bỏ qua cho đồ thị
```

---

## 9. Bộ Kịch Bản Kiểm Thử & Xác Minh Hệ Thống (System Validation Suite)

Dự án tích hợp bộ kịch bản tự động hóa trong thư mục `scripts/validation/` để xác minh độ ổn định và chất lượng hệ thống trên cả Windows Host cục bộ và Docker container:

* **Kiểm tra cú pháp (`check_syntax.ps1` / `.sh`):** Quét lỗi biên dịch python và chạy Ruff linter cho backend, ESLint cho frontend.
* **Bộ Unit Test Fail-Fast (`run_unit_tests.ps1` / `.sh`):** Khởi chạy pytest suite với cờ exit-first `-x` và đo đạc thời gian chạy test (`--durations=5`).
* **Đánh giá rò rỉ SSE (`detect_sse_leaks.ps1` / `.sh`):** Tự động mô phỏng client ngắt kết nối SSE đột ngột để kiểm tra rò rỉ số luồng (threads) của Backend và socket outbound tới cổng 443 Wikidata.
* **Stress Test RAM & Kết nối Redis (`stress_memory.ps1` / `.sh`):** Giả lập tạm dừng (pause) Redis container và sử dụng `autocannon` tạo tải giả lập để xác nhận giới hạn RAM của `BoundedLRUCache` (50,000 nodes).
* **SPARQL Performance Benchmark (`benchmark_sparql.ps1` / `.sh`):** Đo đạc thời gian phản hồi thực tế của Wikidata SPARQL endpoint đối với câu truy vấn cũ và mới, loại bỏ CDN Cache bằng cờ `no-cache` và các tham số ngẫu nhiên.
