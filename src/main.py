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

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Bắt và in chi tiết lỗi validation cùng dữ liệu thô từ client Unity."""
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8", errors="replace")
    logger.error("❌ [422 Validation Error] Chi tiết lỗi: %s", exc.errors())
    logger.error("📥 [Raw JSON từ Unity]: %s", body_str)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "raw_received": body_str},
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
