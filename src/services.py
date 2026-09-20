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
from google.genai import types

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

# Khởi tạo Gemini client một lần duy nhất (Singleton pattern) với timeout 10 giây
gemini_client = genai.Client(
    api_key=GOOGLE_API_KEY,
    http_options=types.HttpOptions(timeout=10000),
)
logger.info("✅ Đã khởi tạo Gemini client thành công, model: %s", GEMINI_MODEL)

# Bảng chi phí mặt trời chuẩn của các loại cây
PLANT_COSTS: dict[str, int] = {
    "SunFlower": 50,
    "PeaShooter": 100,
    "PeaShooterSingle": 100,
    "WallNut": 50,
    "Squash": 50,
    "TorchWood": 175,
    "SnowKing": 175,
    "MiaoMiao": 50,
    "FireWallNutFusion": 100,
}


def get_plant_cost(plant_name: str) -> int:
    """Tra cứu chi phí mặt trời của cây (mặc định 50 nếu không rõ)."""
    for name, cost in PLANT_COSTS.items():
        if name.lower() == plant_name.lower():
            return cost
    return 50


# System prompt huấn luyện LLM kèm tri thức đặc thù của PvZ2 Fusion
SYSTEM_PROMPT = """Bạn là trợ lý AI chiến thuật cấp cao cho game Plants vs Zombies 2D Fusion.
Nhiệm vụ: Phân tích trạng thái trận đấu thời gian thực và đưa ra MỘT lời khuyên chiến thuật duy nhất, ngắn gọn, chuẩn xác.

TRI THỨC VỀ CÁC LOẠI CÂY (PLANTS):
- SunFlower (50☀️): Tạo mặt trời. Ban đêm bắt buộc phải trồng nhiều vì không có mặt trời rơi tự nhiên.
- PeaShooter (100☀️): Bắn đậu theo hàng, dùng phòng thủ cơ bản.
- WallNut (50☀️, 4000HP): Chặn đường zombie, câu giờ cực tốt.
- Squash (50☀️): Đè bẹp 1 zombie gây sát thương cực lớn rồi biến mất (dùng diệt BucketZombie, zombie khẩn cấp).
- TorchWood (175☀️): Sưởi ấm cây xung quanh (hóa giải trạng thái Cold), biến đạn đậu thành đạn lửa gây x2 sát thương.
- SnowKing (175☀️): Cây buff toàn sân (intensified=true).
- MiaoMiao (50☀️): Ký sinh zombie, hút 1% máu/giây và hồi máu cho cây.
- FireWallNutFusion (100☀️): Cây lai vừa chịu đòn cực trâu vừa phản sát thương lửa.

TRI THỨC VỀ CÁC LOẠI ZOMBIE:
- ZombieNormal (270HP): Zombie cơ bản.
- ConeZombie (560HP): Máu trung bình.
- BucketZombie (1370HP), IceBlockZombie: Máu cực trâu, cần nhiều PeaShooter, đạn lửa TorchWood hoặc Squash khẩn cấp.
- SnowZombie: Tấn công làm đóng băng cây (state=Cold, giảm 50% tốc độ bắn, mất 8HP/s). Cần TorchWood để giải băng!
- Tọa độ posX: posX càng nhỏ càng gần nhà (game over). Nếu posX < 0 là cực kỳ nguy hiểm, posX < -3 là sắp thua!

QUY ƯỚC LƯỚI SÂN CỎ (5 Hàng × 9 Cột, đánh số từ 1):
- HÀNG: từ Hàng 1 (trên cùng) đến Hàng 5 (dưới cùng).
- CỘT: từ Cột 1 (sát nhà) đến Cột 9 (ngoài cùng bên phải).

QUY TẮC BẮT BUỘC KHI ĐƯA LỜI KHUYÊN:
1. Trả lời BẰNG TIẾNG VIỆT.
2. Chỉ viết đúng 1 câu duy nhất, độ dài TỐI ĐA 180 ký tự.
3. Chỉ rõ chính xác Hàng và Cột (ví dụ: "Hàng 1, Cột 1", "Hàng 3, Cột 2", "Hàng 4, Cột 1"). KHÔNG thêm các mô tả rườm rà như "(sát hàng rào)", "(sát nhà)", "(giữa sân)", "(dưới cùng)".
4. QUY TẮC MẶT TRỜI & TÀI CHÍNH (CỰC KỲ QUAN TRỌNG):
   - Khi ĐỦ MẶT TRỜI (currentSun >= giá cây): Khuyên trồng trực tiếp. Cú pháp: "Trồng [Tên cây] tại [Hàng X, Cột Y]..."
   - Khi KHÔNG ĐỦ MẶT TRỜI (currentSun < giá cây hoặc không đủ tiền trồng bất kỳ cây nào):
     + TUYỆT ĐỐI KHÔNG dùng từ "Trồng..." như thể có thể trồng được ngay lập tức!
     + BẮT BUỘC khuyên người chơi CHỜ hoặc TÍCH LŨY MẶT TRỜI.
     + Cú pháp chuẩn: "Chờ gom đủ [giá cây] mặt trời để trồng [Tên cây] tại [Hàng X, Cột Y]..." hoặc "Chờ thu thập đủ [giá cây] mặt trời để..."
     + Ví dụ: Nếu hiện có 0☀️ và muốn trồng SunFlower (giá 50☀️), PHẢI KHUYÊN: "Chờ gom đủ 50 mặt trời để trồng SunFlower tại Hàng 1, Cột 1." (TUYỆT ĐỐI KHÔNG NÓI "Trồng SunFlower tại Hàng 1, Cột 1").
5. Ưu tiên hàng đầu: Bảo vệ hàng có zombie nguy hiểm/gần nhà nhất (posX < 0), hoặc cứu cây sắp chết (máu < 20%), hoặc cứu cây bị đóng băng.
6. Chỉ gợi ý loại cây có trong thẻ (availablePlantCards) và đặt vào ô còn trống (emptyGrids).
7. Chỉ trả về lời khuyên hành động hoặc chờ đợi, KHÔNG chào hỏi, KHÔNG giải thích dài dòng.
"""


def format_row(row: int) -> str:
    """Định dạng tên hàng 1-indexed (Hàng 1 đến Hàng 5)."""
    return f"Hàng {row + 1}"


def format_col(col: int) -> str:
    """Định dạng tên cột 1-indexed (Cột 1 đến Cột 9)."""
    return f"Cột {col + 1}"


def format_state_for_llm(state: GameStateSnapshot) -> str:
    """
    Tiền xử lý và tóm tắt trạng thái trận đấu thành chuỗi văn bản cho AI.
    Áp dụng các luật lọc theo Mục 6.2:
      - Top 3 zombie nguy hiểm nhất (posX nhỏ nhất = gần nhà nhất)
      - Cây gặp nguy hiểm: máu yếu (< 20%) hoặc bị đóng băng ('Cold')
      - Tối đa 5 ô đất trống gần nhà nhất (col nhỏ nhất)
      - Đánh giá khả năng tài chính (mặt trời) và tính khả thi của các thẻ bài
    """
    lines: list[str] = []

    # 1. Thông tin tổng quan màn chơi
    time_of_day = (
        "Ban ngày (có mặt trời rơi tự nhiên)"
        if state.isDay
        else "Ban đêm (KHÔNG có mặt trời rơi, phải trồng SunFlower)"
    )
    lines.append(f"🗺️ Màn chơi: {state.levelName} | {time_of_day}")
    lines.append(
        f"☀️ Mặt trời hiện có: {state.currentSun} | Đợt: {state.currentWave + 1}/{state.totalWaves}"
    )
    lines.append(
        f"🧟 Zombie trên sân: {state.zombiesOnField} con | Đợt kế tiếp: {state.nextWaveZombieType}"
    )

    cards = state.availablePlantCards or []
    if cards:
        card_desc = []
        affordable_cards = []
        for c in cards:
            cost = get_plant_cost(c)
            if state.currentSun >= cost:
                card_desc.append(f"{c} (giá {cost}☀️ - [ĐỦ TIỀN])")
                affordable_cards.append(c)
            else:
                card_desc.append(
                    f"{c} (giá {cost}☀️ - [THIẾU {cost - state.currentSun}☀️])"
                )
        lines.append(f"🃏 Thẻ cây có sẵn: {', '.join(card_desc)}")

        if not affordable_cards:
            min_cost = min(get_plant_cost(c) for c in cards)
            lines.append(
                f"⚠️ TÌNH TRẠNG MẶT TRỜI: Hiện có {state.currentSun}☀️, KHÔNG ĐỦ để trồng bất kỳ cây nào (cần tối thiểu {min_cost}☀️)!"
                f"\n👉 QUY TẮC BẮT BUỘC: Hiện chưa thể trồng cây ngay! Phải khuyên người chơi 'Chờ gom đủ {min_cost} mặt trời để trồng [Tên cây] tại [Vị trí]'."
            )
        else:
            lines.append(f"💰 Cây đủ tiền trồng ngay: {', '.join(affordable_cards)}")
    else:
        lines.append("🃏 Thẻ cây có sẵn: Không có")

    # 2. Lọc top 3 zombie nguy hiểm nhất (sắp xếp theo posX tăng dần)
    zombies_list = state.zombies or []
    sorted_zombies = sorted(zombies_list, key=lambda z: z.posX)
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
            row_desc = format_row(z.row)
            lines.append(
                f"  - {z.type} | {row_desc} | posX={z.posX:.1f} | "
                f"HP: {z.hp}/{z.maxHp} ({hp_pct}%) | Trạng thái: {z.state}{danger_label}"
            )

    # 3. Lọc cây đang gặp nguy hiểm (máu < 20% hoặc bị đóng băng)
    plants_list = state.plants or []
    endangered_plants: list[PlantInfo] = []
    for p in plants_list:
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
            row_desc = format_row(p.row)
            col_desc = format_col(p.col)
            lines.append(
                f"  - {p.type} | {row_desc}, {col_desc} | "
                f"HP: {p.hp}/{p.maxHp} | Vấn đề: {', '.join(issues)}"
            )

    # 4. Lấy 5 ô đất trống gần nhà nhất (col nhỏ nhất)
    grids_list = state.emptyGrids or []
    sorted_grids = sorted(grids_list, key=lambda g: (g.col, g.row))
    top_empty_grids = sorted_grids[:5]

    if top_empty_grids:
        lines.append("\n📍 Ô TRỐNG GẦN NHÀ (có thể trồng cây):")
        for g in top_empty_grids:
            row_desc = format_row(g.row)
            col_desc = format_col(g.col)
            lines.append(f"  - {row_desc}, {col_desc}")

    # 5. Thống kê phân bổ và vị trí cây hiện tại
    if plants_list:
        lines.append(f"\n🌱 Cây hiện có trên sân ({len(plants_list)} cây):")
        for p in plants_list[:8]:
            row_desc = format_row(p.row)
            col_desc = format_col(p.col)
            lines.append(f"  - {p.type} tại {row_desc}, {col_desc}")
        if len(plants_list) > 8:
            lines.append(f"  ... và {len(plants_list) - 8} cây khác.")

    return "\n".join(lines)


def enforce_sun_advice_rule(advice: str, state: GameStateSnapshot) -> str:
    """
    Hàng rào bảo vệ (Guardrail): Đảm bảo không bao giờ khuyên 'Trồng cây...'
    khi người chơi chưa đủ số mặt trời cần thiết. Tự động chuyển ngữ cảnh sang 'Chờ gom đủ...'.
    """
    advice_strip = advice.strip()
    action_prefixes = ["Trồng ", "Hãy trồng ", "Nên trồng "]
    matched_prefix = None
    for p in action_prefixes:
        if advice_strip.startswith(p):
            matched_prefix = p
            break

    if not matched_prefix:
        return advice_strip

    # Tìm loại cây được nhắc đến trong câu khuyên
    target_plant = None
    target_cost = 50
    for p_name, cost in sorted(PLANT_COSTS.items(), key=lambda x: -len(x[0])):
        if p_name.lower() in advice_strip.lower():
            target_plant = p_name
            target_cost = cost
            break

    if not target_plant and state.availablePlantCards:
        target_cost = min(get_plant_cost(c) for c in state.availablePlantCards)

    # Nếu số mặt trời hiện tại không đủ để trồng cây này
    if state.currentSun < target_cost:
        rest = advice_strip[len(matched_prefix) :]
        return f"Chờ gom đủ {target_cost} mặt trời để trồng {rest}"

    return advice_strip


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

        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
            temperature=0.2,
        )

        response = await gemini_client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )

        # Trích xuất văn bản an toàn (phòng ngừa response.text = None)
        raw_text = response.text or ""
        advice_text = raw_text.strip()

        if not advice_text:
            advice_text = (
                "Tình hình căng thẳng, hãy cẩn thận phòng thủ và theo dõi các hàng!"
            )
        else:
            # Áp dụng guardrail kiểm tra số mặt trời trước khi trả về cho client
            advice_text = enforce_sun_advice_rule(advice_text, state)

        if len(advice_text) > 200:
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

