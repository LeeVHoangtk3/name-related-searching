#!/bin/bash
# Script: stress_memory.sh
# Ý nghĩa: Giả lập ngắt kết nối Redis và benchmark bộ nhớ container Backend ghi log CSV để xác minh LRU cache 50k nodes.

CSV_FILE="ram_profile.csv"
BENCHMARK_URL="http://localhost:8000/api/search?start=Q5&target=Q42&mode=deep"
DURATION=30
CONCURRENCY=50

echo -e "\033[0;33mGiả lập lỗi kết nối bằng cách pause container Redis...\033[0m"
docker compose pause redis || echo "Cảnh báo: Không thể pause redis. Đảm bảo redis container đang chạy."

# Tìm container ID của backend
BACKEND_CID=$(docker compose ps -q backend)
if [ -z "$BACKEND_CID" ]; then
    echo -e "\033[0;31mKhông tìm thấy container backend đang chạy! Hủy bỏ stress test.\033[0m"
    docker compose unpause redis 2>/dev/null || true
    exit 1
fi

echo "Giám sát container: $BACKEND_CID"
echo "Timestamp,Source,Memory_Usage,CPU_Percentage" > "$CSV_FILE"

# Chạy loop giám sát ngầm ghi log tài nguyên
monitor_resources() {
    while true; do
        TS=$(date "+%Y-%m-%d %H:%M:%S")
        # docker stats format: "MEM USAGE / LIMIT | CPU %"
        STATS=$(docker stats --no-stream "$BACKEND_CID" --format "{{.MemUsage}},{{.CPUPerc}}")
        echo "$TS,DockerContainer,$STATS" >> "$CSV_FILE"
        sleep 2
    done
}

# Khởi chạy hàm giám sát ở background
monitor_resources &
MONITOR_PID=$!

echo -e "\033[0;36m=== BẮT ĐẦU CHẠY STRESS TEST (autocannon) ===\033[0m"
echo "Benchmark URL: $BENCHMARK_URL"
echo "Thời gian: $DURATION giây | Kết nối: $CONCURRENCY"

# Sử dụng autocannon cài cục bộ hoặc npx
if command -v autocannon &> /dev/null; then
    autocannon -c "$CONCURRENCY" -d "$DURATION" -m GET "$BENCHMARK_URL"
else
    npx autocannon -c "$CONCURRENCY" -d "$DURATION" -m GET "$BENCHMARK_URL"
fi

# Tắt tiến trình giám sát ngầm
kill "$MONITOR_PID" 2>/dev/null || true

echo -e "\033[0;33mKhôi phục Redis container...\033[0m"
docker compose unpause redis || true

echo -e "\033[0;36m=== KẾT QUẢ GHI NHẬN RAM TRONG FILE LOG ($CSV_FILE) ===\033[0m"
tail -n 10 "$CSV_FILE"

echo -e "\033[0;32mOOM Stress Test Hoàn tất!\033[0m"
exit 0
