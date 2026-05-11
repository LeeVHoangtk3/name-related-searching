from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes

app = FastAPI(title="WikiBFS API")

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
