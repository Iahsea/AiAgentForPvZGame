"""
=============================================================================
  PvZ2 Fusion — Pydantic Schemas / Models
  -------------------------------------------------------------------------
  Định nghĩa chính xác 100% schema DTO (Data Transfer Object) từ Mục 2.2 & 2.3
  trong tài liệu kiến trúc.
=============================================================================
"""

from typing import List
from pydantic import BaseModel, Field


class PlantInfo(BaseModel):
    """Thông tin từng cây đang trồng trên sân cỏ."""
    type: str = Field(..., description="Tên loại cây (vd: SunFlower, PeaShooter)")
    row: int = Field(..., ge=0, le=4, description="Hàng đứng (0-4, từ trên xuống)")
    col: int = Field(..., ge=0, le=8, description="Cột đứng (0-8, từ trái sang)")
    posX: float = Field(..., description="Tọa độ X world space")
    posY: float = Field(..., description="Tọa độ Y world space")
    hp: int = Field(..., ge=0, description="Máu hiện tại")
    maxHp: int = Field(..., gt=0, description="Máu tối đa ban đầu")
    state: str = Field(..., description="Trạng thái: Normal | Warm | Cold")
    intensified: bool = Field(..., description="True nếu được SnowKing buff")


class ZombieInfo(BaseModel):
    """Thông tin từng zombie đang sống trên sân cỏ."""
    type: str = Field(..., description="Tên loại zombie (vd: BucketZombie)")
    row: int = Field(..., ge=0, le=4, description="Hàng di chuyển (0-4)")
    posX: float = Field(..., description="Tọa độ X — càng nhỏ càng gần nhà")
    hp: int = Field(..., ge=0, description="Máu hiện tại")
    maxHp: int = Field(..., gt=0, description="Máu tối đa ban đầu")
    state: str = Field(..., description="Trạng thái: Normal | Cold | Parasiticed")


class GridInfo(BaseModel):
    """Thông tin một ô đất trống có thể trồng cây mới."""
    row: int = Field(..., ge=0, le=4, description="Hàng (0-4)")
    col: int = Field(..., ge=0, le=8, description="Cột (0-8)")
    posX: float = Field(..., description="Tọa độ X world space")
    posY: float = Field(..., description="Tọa độ Y world space")


class GameStateSnapshot(BaseModel):
    """
    Snapshot toàn bộ trạng thái trận đấu từ Unity gửi lên.
    Khớp 100% schema Mục 2.2.
    """
    level: int = Field(..., ge=0, description="Số thứ tự màn chơi (0-indexed)")
    levelName: str = Field(..., description="Tên màn chơi (vd: Vườn Băng Tuyết)")
    isDay: bool = Field(..., description="True = ban ngày, False = ban đêm")
    currentSun: int = Field(..., ge=0, description="Số mặt trời hiện có")
    currentWave: int = Field(..., ge=0, description="Đợt zombie hiện tại (0-indexed)")
    totalWaves: int = Field(..., gt=0, description="Tổng số đợt zombie")
    zombiesOnField: int = Field(..., ge=0, description="Số zombie đang sống trên sân")
    nextWaveZombieType: str = Field(..., description="Loại zombie đợt kế tiếp hoặc 'Hết đợt'")
    availablePlantCards: List[str] = Field(default_factory=list, description="Thẻ cây được phép dùng")
    plants: List[PlantInfo] = Field(default_factory=list, description="Danh sách cây trên sân")
    zombies: List[ZombieInfo] = Field(default_factory=list, description="Danh sách zombie trên sân")
    emptyGrids: List[GridInfo] = Field(default_factory=list, description="Danh sách ô đất trống")


class AIResponse(BaseModel):
    """Phản hồi trả về cho client Unity (Mục 2.3)."""
    advice: str = Field(..., description="Lời khuyên chiến thuật bằng tiếng Việt, ≤ 200 ký tự")
    status: str = Field(default="ok", description="'ok' khi thành công, 'error' khi có sự cố")
