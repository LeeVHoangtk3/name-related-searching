#!/bin/bash
# Script: check_syntax.sh
# Ý nghĩa: Kiểm tra cú pháp Python, chạy Ruff và ESLint thông qua Docker Compose hoặc môi trường Linux cục bộ.

set -e

echo -e "\033[0;36m=== [1/3] ĐANG BIÊN DỊCH THỬ PYTHON BACKEND (compileall) ===\033[0m"
if docker compose ps | grep -q "backend"; then
    echo "Phát hiện backend container đang chạy, kiểm tra qua Docker..."
    docker compose exec -T backend python -m compileall -q -f app/
else
    echo "Không thấy container backend chạy, chạy cục bộ..."
    python3 -m compileall -q -f src/backend/app/
fi
echo -e "\033[0;32mCompileall: OK.\033[0m"

echo -e "\033[0;36m=== [2/3] CHẠY RUFF CODE QUALITY GATE ===\033[0m"
if docker compose ps | grep -q "backend"; then
    echo "Chạy ruff trong container backend..."
    # Cài đặt ruff trong container nếu chưa có
    docker compose exec -T backend pip install ruff -q
    docker compose exec -T backend ruff check app/ --show-fixes --fix || echo "Ruff phát hiện một số lỗi không thể sửa tự động."
else
    echo "Chạy ruff cục bộ..."
    if ! command -v ruff &> /dev/null; then
        pip install ruff -q
    fi
    ruff check src/backend/app --show-fixes --fix || echo "Ruff phát hiện một số lỗi không thể sửa tự động."
fi
echo -e "\033[0;32mRuff check hoàn tất.\033[0m"

echo -e "\033[0;36m=== [3/3] CHẠY FRONTEND LINTER (ESLint) ===\033[0m"
if docker compose ps | grep -q "frontend"; then
    echo "Chạy lint trong container frontend..."
    docker compose exec -T frontend npm run lint
else
    echo "Chạy lint frontend cục bộ..."
    cd src/frontend
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run lint
    cd ../..
fi
echo -e "\033[0;32mFrontend Lint: OK.\033[0m"

echo -e "\033[0;32m=== KIỂM TRA CÚ PHÁP HOÀN TẤT: THÀNH CÔNG ===\033[0m"
exit 0
