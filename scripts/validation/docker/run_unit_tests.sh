#!/bin/bash
# Script: run_unit_tests.sh
# Ý nghĩa: Chạy bộ kiểm thử pytest trong Docker backend container hoặc môi trường local với cờ Fail-Fast và đo thời gian test.

set -e

echo -e "\033[0;36m=== ĐANG KHỞI CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (pytest) ===\033[0m"

if docker compose ps | grep -q "backend"; then
    echo "Chạy pytest bên trong container backend..."
    # Cài đặt các thư viện test nếu chưa có trong container
    docker compose exec -T backend pip install pytest pytest-asyncio pytest-cov httpx -q
    docker compose exec -T backend sh -c "PYTHONPATH=. pytest -v -x --tb=short --durations=5"
else
    echo "Chạy pytest cục bộ..."
    cd src/backend
    if [ -f "../../venv/bin/pytest" ]; then
        ../../venv/bin/pip install pytest pytest-asyncio pytest-cov httpx -q
        PYTHONPATH=. ../../venv/bin/pytest -v -x --tb=short --durations=5
    else
        if ! command -v pytest &> /dev/null; then
            pip install pytest pytest-asyncio pytest-cov httpx -q
        fi
        PYTHONPATH=. pytest -v -x --tb=short --durations=5
    fi
    cd ../..
fi

echo -e "\033[0;32m=== BỘ KIỂM THỬ CHẠY THÀNH CÔNG (FAIL-FAST PASSED) ===\033[0m"
exit 0
