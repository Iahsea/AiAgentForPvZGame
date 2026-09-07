"""
=============================================================================
  PvZ2 Fusion — API Router / Controller Layer
  -------------------------------------------------------------------------
  Đóng vai trò Controller: tiếp nhận HTTP request từ client, điều phối sang
  Service layer để xử lý và trả về HTTP response tương ứng.
=============================================================================
"""

from fastapi import APIRouter
from src.models import GameStateSnapshot, AIResponse
from src.services import generate_tactical_advice, GEMINI_MODEL

router = APIRouter(tags=["AI Advisor"])


@router.post("/analyze", response_model=AIResponse, summary="Phân tích trận đấu và đưa ra lời khuyên")
async def analyze_game_state(state: GameStateSnapshot) -> AIResponse:
    """
    Endpoint chính nhận snapshot trạng thái game từ Unity client.
    Ủy quyền hoàn toàn cho Service layer xử lý logic.
    """
    return await generate_tactical_advice(state)


@router.get("/health", summary="Kiểm tra trạng thái server")
async def health_check():
    """Endpoint dùng cho health check và monitoring."""
    return {"status": "ok", "model": GEMINI_MODEL}
