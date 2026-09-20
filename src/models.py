"""
=============================================================================
  PvZ2 Fusion — Pydantic Schemas / Models
  -------------------------------------------------------------------------
  Định nghĩa chính xác 100% schema DTO (Data Transfer Object) từ Mục 2.2 & 2.3
  trong tài liệu kiến trúc.
=============================================================================
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class PlantInfo(BaseModel):
    """Thông tin từng cây đang trồng trên sân cỏ."""
    type: str = "Unknown"
    row: int = 0
    col: int = 0
    posX: float = 0.0
    posY: float = 0.0
    hp: int = 0
    maxHp: int = 1
    state: str = "Normal"
    intensified: bool = False


class ZombieInfo(BaseModel):
    """Thông tin từng zombie đang sống trên sân cỏ."""
    type: str = "ZombieNormal"
    row: int = 0
    posX: float = 0.0
    hp: int = 0
    maxHp: int = 1
    state: str = "Normal"


class GridInfo(BaseModel):
    """Thông tin một ô đất trống có thể trồng cây mới."""
    row: int = 0
    col: int = 0
    posX: float = 0.0
    posY: float = 0.0


class GameStateSnapshot(BaseModel):
    """
    Snapshot toàn bộ trạng thái trận đấu từ Unity gửi lên.
    Hỗ trợ giá trị mặc định và danh sách rỗng để chống lỗi 422 nếu client gửi thiếu trường.
    """
    level: int = 0
    levelName: str = ""
    isDay: bool = True
    currentSun: int = 0
    currentWave: int = 0
    totalWaves: int = 0
    zombiesOnField: int = 0
    nextWaveZombieType: str = ""
    availablePlantCards: Optional[List[str]] = Field(default_factory=list)
    plants: Optional[List[PlantInfo]] = Field(default_factory=list)
    zombies: Optional[List[ZombieInfo]] = Field(default_factory=list)
    emptyGrids: Optional[List[GridInfo]] = Field(default_factory=list)


class AIResponse(BaseModel):
    """Phản hồi trả về cho client Unity (Mục 2.3)."""
    advice: str = Field(..., description="Lời khuyên chiến thuật bằng tiếng Việt, ≤ 200 ký tự")
    status: str = Field(default="ok", description="'ok' khi thành công, 'error' khi có sự cố")
