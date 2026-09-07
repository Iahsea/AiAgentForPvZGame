"""
=============================================================================
  PvZ2 Fusion — Application Entry Point (FastAPI Bootstrap)
  -------------------------------------------------------------------------
  Khởi tạo ứng dụng FastAPI, đăng ký middleware, gắn Router, và uvicorn server.
=============================================================================
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import router as advisor_router

# ---------------------------------------------------------------------------
# Cấu hình Logging tập trung
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("pvz_advisor")

# ---------------------------------------------------------------------------
# Khởi tạo FastAPI Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PvZ2 Fusion — AI Advisor API",
    description="Backend AI phân tích chiến thuật thời gian thực cho game PvZ2 Fusion.",
    version="1.1.0",
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký Controller / Router
app.include_router(advisor_router)


# ---------------------------------------------------------------------------
# Entry point khi chạy trực tiếp qua `python -m src.main`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
