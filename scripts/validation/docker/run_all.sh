#!/bin/bash
# Script: run_all.sh
# Ý nghĩa: Kịch bản tổng hợp chạy toàn bộ các bước kiểm tra chất lượng hệ thống cho môi trường Linux/Docker.

set -e

# Đảm bảo ta đang ở đúng thư mục của script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "\033[0;36m========================================================\033[0m"
echo -e "\033[0;36m   BẮT ĐẦU CHẠY TOÀN BỘ BỘ XÁC MINH HỆ THỐNG WIKIBFS    \033[0m"
echo -e "\033[0;36m========================================================\033[0m"

run_sub_script() {
    local script_name=$1
    echo -e "\n\033[0;32m>>> ĐANG CHẠY: $script_name...\033[0m"
    bash "$SCRIPT_DIR/$script_name"
}

# Chạy tuần tự các kịch bản kiểm tra
run_sub_script "check_syntax.sh"
run_sub_script "run_unit_tests.sh"
run_sub_script "benchmark_sparql.sh"
run_sub_script "detect_sse_leaks.sh"
run_sub_script "stress_memory.sh"

echo -e "\n\033[0;32m========================================================\033[0m"
echo -e "\033[0;32m   XÁC MINH TOÀN BỘ HỆ THỐNG: HOÀN TẤT & THÀNH CÔNG!    \033[0m"
echo -e "\033[0;32m========================================================\033[0m"
exit 0
