"""
=============================================================================
  PvZ2 Fusion — AI Advisor Service (Business Logic & LLM)
  -------------------------------------------------------------------------
  Chứa toàn bộ nghiệp vụ:
    1. Tiền xử lý dữ liệu (Pre-processing State theo Mục 6.2)
    2. Tích hợp Google Gemini AI và sinh lời khuyên chiến thuật (Mục 6.3)
    3. Xử lý lỗi ngoại lệ, an toàn kiểu dữ liệu (safe response text extraction)
=============================================================================
"""

import os
import logging
from dotenv import load_dotenv
from google import genai

from src.models import GameStateSnapshot, PlantInfo, AIResponse

logger = logging.getLogger(__name__)

# Load biến môi trường
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL: str = os.getenv("MODEL", "models/gemini-2.0-flash-lite")

if not GOOGLE_API_KEY:
    raise RuntimeError(
        "⚠️ Thiếu GOOGLE_API_KEY trong biến môi trường. "
        "Hãy kiểm tra file src/.env với GOOGLE_API_KEY=<your-key>"
    )

# Khởi tạo Gemini client một lần duy nhất (Singleton pattern)
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
logger.info("✅ Đã khởi tạo Gemini client thành công, model: %s", GEMINI_MODEL)

# System prompt huấn luyện LLM
SYSTEM_PROMPT = """Bạn là trợ lý AI chiến thuật cho game Plants vs Zombies 2D Fusion.
Nhiệm vụ: Phân tích trạng thái trận đấu và đưa ra MỘT lời khuyên chiến thuật duy nhất.

QUY TẮC BẮT BUỘC:
1. Trả lời BẰNG TIẾNG VIỆT.
2. Chỉ viết đúng 1 câu duy nhất.
3. Câu trả lời KHÔNG ĐƯỢC vượt quá 200 ký tự.
4. Tập trung vào hành động cụ thể nhất, ưu tiên xử lý tình huống nguy cấp trước.
5. Nếu có zombie sắp tới nhà (posX < 0), ưu tiên cảnh báo ngay.
6. Nếu ban đêm, nhắc trồng SunFlower nếu chưa đủ.
7. Chỉ trả về lời khuyên, KHÔNG giải thích, KHÔNG thêm tiêu đề.

VÍ DỤ LỜI KHUYÊN TỐT:
- "Hàng 2 trống, BucketZombie đang tới! Trồng WallNut cột 1 hàng 2 để chặn, đặt PeaShooter phía sau."
- "Mặt trời thấp, trồng thêm SunFlower ở hàng 3 cột 0 để tăng thu nhập."
- "PeaShooter hàng 0 bị đóng băng, trồng TorchWood cạnh đó để sưởi ấm ngay!"
"""


def format_state_for_llm(state: GameStateSnapshot) -> str:
    """
    Tiền xử lý và tóm tắt trạng thái trận đấu thành chuỗi văn bản cho AI.
    Áp dụng các luật lọc theo Mục 6.2:
      - Top 3 zombie nguy hiểm nhất (posX nhỏ nhất = gần nhà nhất)
      - Cây gặp nguy hiểm: máu yếu (< 20%) hoặc bị đóng băng ('Cold')
      - Tối đa 5 ô đất trống gần nhà nhất (col nhỏ nhất)
    """
    lines: list[str] = []

    # 1. Thông tin tổng quan màn chơi
    time_of_day = (
        "Ban ngày (có mặt trời rơi tự nhiên)"
        if state.isDay
        else "Ban đêm (KHÔNG có mặt trời rơi, phải trồng SunFlower)"
    )
    lines.append(f"🗺️ Màn chơi: {state.levelName} | {time_of_day}")
    lines.append(f"☀️ Mặt trời: {state.currentSun} | Đợt: {state.currentWave + 1}/{state.totalWaves}")
    lines.append(f"🧟 Zombie trên sân: {state.zombiesOnField} con | Đợt kế tiếp: {state.nextWaveZombieType}")
    lines.append(f"🃏 Thẻ cây có sẵn: {', '.join(state.availablePlantCards)}")

    # 2. Lọc top 3 zombie nguy hiểm nhất (sắp xếp theo posX tăng dần)
    sorted_zombies = sorted(state.zombies, key=lambda z: z.posX)
    top_dangerous_zombies = sorted_zombies[:3]

    if top_dangerous_zombies:
        lines.append("\n⚠️ ZOMBIE NGUY HIỂM NHẤT (gần nhà nhất):")
        for z in top_dangerous_zombies:
            hp_pct = round(z.hp / z.maxHp * 100) if z.maxHp > 0 else 0
            danger_label = ""
            if z.posX < -3.0:
                danger_label = " 🔴 SẮP THUA! Zombie gần nhà cực kỳ nguy hiểm!"
            elif z.posX < 0:
                danger_label = " 🟠 NGUY HIỂM! Zombie đã vào khu vực gần nhà!"
            lines.append(
                f"  - {z.type} | Hàng {z.row} | posX={z.posX:.1f} | "
                f"HP: {z.hp}/{z.maxHp} ({hp_pct}%) | Trạng thái: {z.state}{danger_label}"
            )

    # 3. Lọc cây đang gặp nguy hiểm (máu < 20% hoặc bị đóng băng)
    endangered_plants: list[PlantInfo] = []
    for p in state.plants:
        hp_ratio = p.hp / p.maxHp if p.maxHp > 0 else 0
        is_low_hp = hp_ratio < 0.2
        is_frozen = p.state == "Cold"
        if is_low_hp or is_frozen:
            endangered_plants.append(p)

    if endangered_plants:
        lines.append("\n🌿 CÂY ĐANG GẶP NGUY HIỂM:")
        for p in endangered_plants:
            hp_ratio = p.hp / p.maxHp if p.maxHp > 0 else 0
            issues: list[str] = []
            if hp_ratio < 0.2:
                issues.append(f"MÁU YẾU ({round(hp_ratio * 100)}%)")
            if p.state == "Cold":
                issues.append("BỊ ĐÓNG BĂNG (cần TorchWood sưởi ấm)")
            lines.append(
                f"  - {p.type} | Hàng {p.row}, Cột {p.col} | "
                f"HP: {p.hp}/{p.maxHp} | Vấn đề: {', '.join(issues)}"
            )

    # 4. Lấy 5 ô đất trống gần nhà nhất (col nhỏ nhất)
    sorted_grids = sorted(state.emptyGrids, key=lambda g: (g.col, g.row))
    top_empty_grids = sorted_grids[:5]

    if top_empty_grids:
        lines.append("\n📍 Ô TRỐNG GẦN NHÀ (có thể trồng cây):")
        for g in top_empty_grids:
            lines.append(f"  - Hàng {g.row}, Cột {g.col}")

    # 5. Thống kê phân bổ cây hiện tại
    if state.plants:
        lines.append(f"\n🌱 Tổng cây hiện có: {len(state.plants)} cây")
        plant_counts: dict[str, int] = {}
        for p in state.plants:
            plant_counts[p.type] = plant_counts.get(p.type, 0) + 1
        summary_parts = [f"{name}×{count}" for name, count in plant_counts.items()]
        lines.append(f"  Phân bổ: {', '.join(summary_parts)}")

    return "\n".join(lines)


async def generate_tactical_advice(state: GameStateSnapshot) -> AIResponse:
    """
    Hàm nghiệp vụ chính: nhận snapshot, tóm tắt, gọi Gemini, và trả kết quả.
    Tích hợp xử lý lỗi an toàn để Unity client không bị crash.
    """
    try:
        state_summary = format_state_for_llm(state)
        logger.info("📋 State tóm tắt gửi LLM:\n%s", state_summary)

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"--- TRẠNG THÁI TRẬN ĐẤU HIỆN TẠI ---\n"
            f"{state_summary}\n\n"
            f"Hãy đưa ra lời khuyên chiến thuật (1 câu, tiếng Việt, tối đa 200 ký tự):"
        )

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        # Trích xuất văn bản an toàn (phòng ngừa response.text = None)
        raw_text = response.text or ""
        advice_text = raw_text.strip()

        if not advice_text:
            advice_text = "Tình hình căng thẳng, hãy cẩn thận phòng thủ và theo dõi các hàng!"
        elif len(advice_text) > 200:
            # Cắt tại ranh giới câu hoặc từ gần nhất, đảm bảo <= 200 ký tự
            advice_text = advice_text[:197].rsplit(" ", 1)[0] + "..."

        logger.info("🤖 Lời khuyên AI: %s (độ dài: %d)", advice_text, len(advice_text))
        return AIResponse(advice=advice_text, status="ok")

    except Exception as e:
        logger.error("❌ Lỗi khi xử lý AI Service: %s", str(e), exc_info=True)
        # Fallback an toàn cho Unity client
        return AIResponse(
            advice="Lỗi kết nối AI, hãy tự bảo vệ nhà! Trồng WallNut chặn zombie gần nhất.",
            status="error",
        )
