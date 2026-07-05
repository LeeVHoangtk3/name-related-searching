from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes
from app.services.cache_syncer import start_cache_syncer_task, stop_cache_syncer_task

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi chạy cache syncer worker chạy nền
    # Launch background cache syncer worker
    await start_cache_syncer_task()
    yield
    # Hủy tác vụ chạy nền khi dừng server
    # Cancel background task on server shutdown
    await stop_cache_syncer_task()

app = FastAPI(title="WikiBFS API", lifespan=lifespan)

# Cấu hình CORS để cho phép frontend React truy cập
# CORS configuration to allow React frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các routes từ module api
# Register routes from api module
app.include_router(routes.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "WikiBFS API is running"}
