FROM python:3.9-slim

WORKDIR /app

# Cài đặt các dependencies hệ thống cần thiết
# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Sao chép requirements và cài đặt
# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn
# Copy source code
COPY . .

# Chạy ứng dụng với uvicorn
# Run application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
