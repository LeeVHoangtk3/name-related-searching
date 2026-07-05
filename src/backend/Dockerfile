# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies to user local path to keep runtime image clean
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /workspace

# Copy installed user packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application source package directly to `/workspace/app`
# Since PYTHONPATH is /workspace, Python will resolve package imports for `app` to `/workspace/app`.
COPY ./app ./app

# Set environments
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/workspace

EXPOSE 8000

# Run Uvicorn directly
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
