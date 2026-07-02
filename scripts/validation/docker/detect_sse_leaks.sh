#!/bin/bash
# Script: detect_sse_leaks.sh
# Ý nghĩa: Giám sát rò rỉ Thread và kết nối Outbound tới Wikidata (cổng 443) khi các client ngắt kết nối SSE đột ngột.

STREAM_URL="http://localhost:8000/api/search/stream?start=Q5&target=Q42&mode=deep"
CLIENTS_COUNT=5

# 1. Tìm tiến trình Python Backend
# Hỗ trợ chạy trong Docker hoặc Local Linux
if docker compose ps | grep -q "backend"; then
    echo "Tìm tiến trình Python bên trong backend container..."
    BACKEND_PID=$(docker compose exec backend sh -c "pgrep -f uvicorn" | tr -d '\r')
    IN_DOCKER=true
else
    echo "Tìm tiến trình Python chạy cục bộ..."
    BACKEND_PID=$(pgrep -f uvicorn || pgrep -f "app.main:app" | head -n 1)
    IN_DOCKER=false
fi

if [ -z "$BACKEND_PID" ]; then
    echo -e "\033[0;31mKhông tìm thấy tiến trình Backend Python đang chạy! Vui lòng khởi động backend tại cổng 8000 trước.\033[0m"
    exit 1
fi

echo "Tìm thấy Backend PID: $BACKEND_PID"

get_system_metrics() {
    local threads=0
    local conns=0
    
    if [ "$IN_DOCKER" = true ]; then
        # Đo Thread bên trong container
        threads=$(docker compose exec backend sh -c "cat /proc/$BACKEND_PID/status | grep Threads | awk '{print \$2}'" | tr -d '\r')
        # Đo kết nối Outbound Wikidata (cổng 443) từ bên trong container
        conns=$(docker compose exec backend sh -c "netstat -an | grep ':443 ' | grep ESTABLISHED | wc -l" | tr -d '\r')
    else
        # Đo Thread local
        if [ -f "/proc/$BACKEND_PID/status" ]; then
            threads=$(grep Threads "/proc/$BACKEND_PID/status" | awk '{print $2}')
        else
            threads=$(ps -o thcount -p "$BACKEND_PID" | tail -n 1 | awk '{print $1}')
        fi
        # Đo kết nối Outbound Wikidata local
        conns=$(netstat -anp 2>/dev/null | grep "$BACKEND_PID" | grep ":443 " | grep ESTABLISHED | wc -l)
        if [ "$conns" -eq 0 ]; then
            conns=$(ss -antp 2>/dev/null | grep "$BACKEND_PID" | grep -q ":443 " && ss -antp 2>/dev/null | grep "$BACKEND_PID" | grep ":443 " | grep -c ESTABLISHED || echo 0)
        fi
    fi
    
    # Ép kiểu số
    threads=${threads:-0}
    conns=${conns:-0}
    echo "$threads,$conns"
}

# --- BƯỚC 1: ĐO BASELINE ---
echo -e "\033[0;36m=== BƯỚC 1: ĐO THÔNG SỐ BAN ĐẦU (BASELINE) ===\033[0m"
METRICS=$(get_system_metrics)
BASE_THREADS=$(echo "$METRICS" | cut -d',' -f1)
BASE_CONNS=$(echo "$METRICS" | cut -d',' -f2)

echo "Baseline Threads: $BASE_THREADS"
echo "Baseline Outbound HTTPS (443): $BASE_CONNS"

# --- BƯỚC 2: KHỞI TẠO TẢI SSE & ĐÓNG ĐỘT NGỘT ---
echo -e "\n\033[0;36m=== BƯỚC 2: KHỞI CHẠY KHÁCH HÀNG SSE VÀ HỦY ĐỘT NGỘT ===\033[0m"
echo "Đang khởi chạy $CLIENTS_COUNT kết nối SSE đồng thời..."

PIDS=()
for i in $(seq 1 $CLIENTS_COUNT); do
    curl -s -N -H "Accept: text/event-stream" "$STREAM_URL" > /dev/null &
    PIDS+=($!)
done

echo "Đang giữ kết nối trong 2 giây để kích hoạt các luồng BFS..."
sleep 2

# Đo thông số khi đang chạy tải
METRICS_ACTIVE=$(get_system_metrics)
ACTIVE_THREADS=$(echo "$METRICS_ACTIVE" | cut -d',' -f1)
ACTIVE_CONNS=$(echo "$METRICS_ACTIVE" | cut -d',' -f2)
echo -e "\033[0;33mHoạt động Threads: $ACTIVE_THREADS\033[0m"
echo -e "\033[0;33mHoạt động Outbound HTTPS (443): $ACTIVE_CONNS\033[0m"

echo -e "\033[0;31mNgắt đột ngột toàn bộ $CLIENTS_COUNT kết nối (Client abort)...\033[0m"
for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
done

# --- BƯỚC 3: ĐỢI COOLDOWN VÀ PHÂN TÍCH RÒ RỈ ---
COOLDOWN=10
echo -e "\n\033[0;36m=== BƯỚC 3: THEO DÕI GIAI ĐOẠN PHỤC HỒI (COOLDOWN) ===\033[0m"
echo "Đợi $COOLDOWN giây để xem luồng và kết nối có được giải phóng..."
sleep $COOLDOWN

METRICS_CD=$(get_system_metrics)
CD_THREADS=$(echo "$METRICS_CD" | cut -d',' -f1)
CD_CONNS=$(echo "$METRICS_CD" | cut -d',' -f2)
echo -e "\033[0;32mCooldown Threads: $CD_THREADS\033[0m"
echo -e "\033[0;32mCooldown Outbound HTTPS (443): $CD_CONNS\033[0m"

# --- ĐÁNH GIÁ CHUNG ---
echo -e "\n\033[0;36m=== BÁO CÁO PHÂN TÍCH RÒ RỈ ===\033[0m"
THREAD_LEAK=$((CD_THREADS - BASE_THREADS))
CONN_LEAK=$((CD_CONNS - BASE_CONNS))

LEAK_DETECTED=false

if [ "$THREAD_LEAK" -gt 2 ]; then
    echo -e "\033[0;31mCẢNH BÁO: Phát hiện rò rỉ Thread! (Tăng thêm $THREAD_LEAK luồng so với baseline).\033[0m"
    LEAK_DETECTED=true
else
    echo -e "\033[0;32mBộ giải phóng Luồng (Thread GC): HOẠT ĐỘNG TỐT.\033[0m"
fi

if [ "$CONN_LEAK" -gt 1 ]; then
    echo -e "\033[0;31mCẢNH BÁO: Phát hiện rò rỉ kết nối Outbound tới Wikidata! (Còn $CONN_LEAK kết nối treo).\033[0m"
    LEAK_DETECTED=true
else
    echo -e "\033[0;32mBộ giải phóng Kết nối (Outbound Connection GC): HOẠT ĐỘNG TỐT.\033[0m"
fi

if [ "$LEAK_DETECTED" = true ]; then
    echo -e "\033[0;31mKết luận: Phát hiện rò rỉ tài nguyên khi kết nối bị ngắt đột ngột!\033[0m"
    exit 1
else
    echo -e "\033[0;32mKết luận: Không phát hiện rò rỉ. Hệ thống đã được khắc phục triệt để lỗi SSE leaks.\033[0m"
    exit 0
fi
