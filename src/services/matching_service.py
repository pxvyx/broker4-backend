"""
Module  : src/services/matching_service.py
Layer   : Services (Business Logic)
Purpose : Xử lý nghiệp vụ Matching — tìm chuyên gia phù hợp cho Project.

Luồng 7 bước — phụ trách:
    Bước 2 — Matching : find_matches() → List[{expert, score}]

Thuật toán matching (Keyword-based, không dùng AI):
    Tiêu chí 1 (trọng số 30đ/match): required_specialties của Project
                                      khớp với specialties của Expert.
    Tiêu chí 2 (trọng số  8đ/match): Từ khóa trong title của Project
                                      khớp với specialties của Expert.
    Tiêu chí 3 (trọng số  5đ/match): Từ khóa trong title của Project
                                      khớp với available_technologies của Expert.
    → Score cuối được scale về range [60, 95] để đọc dễ hơn.
    → Expert có score = 0 bị loại khỏi kết quả.
"""

import logging
from typing import List, Dict, Any

from src.models.project import Project
from src.models.expert import Expert
from src.repositories.project_repo import ProjectRepository
from src.repositories.expert_repo import ExpertRepository

logger = logging.getLogger(__name__)

_project_repo = ProjectRepository()
_expert_repo = ExpertRepository()


# ── Private helper ─────────────────────────────────────────────────────────────

def _calculate_match_score(project: Project, expert: Expert) -> int:
    """
    Tính điểm tương thích giữa Project và Expert.

    Returns:
        int trong range [60, 95] nếu có ít nhất 1 điểm chung.
        0 nếu hoàn toàn không khớp.
    """
    raw_score = 0

    # ── Tiêu chí 1: required_specialties ↔ expert.specialties ─────────
    # Đây là tiêu chí quan trọng nhất — SME đã khai báo rõ cần chuyên môn gì.
    for req_spec in project.required_specialties:
        req_lower = req_spec.lower()
        for exp_spec in expert.specialties:
            exp_lower = exp_spec.lower()
            # Substring match hai chiều: "Machine Learning" khớp "Machine Learning ứng dụng"
            if req_lower in exp_lower or exp_lower in req_lower:
                raw_score += 30
                break  # Tránh cộng 2 lần cho cùng 1 required_spec

    # ── Tiêu chí 2: title keywords ↔ expert.specialties ───────────────
    title_words = [w for w in project.title.lower().split() if len(w) >= 3]
    for word in title_words:
        for exp_spec in expert.specialties:
            if word in exp_spec.lower():
                raw_score += 8
                break

    # ── Tiêu chí 3: title keywords ↔ expert.available_technologies ────
    for word in title_words:
        for tech in expert.available_technologies:
            if word in tech.lower():
                raw_score += 5
                break

    # ── Score = 0 → không đưa vào kết quả ────────────────────────────
    if raw_score == 0:
        return 0

    # ── Scale về [60, 95]: điểm tối đa lý thuyết ~90 (3 specs × 30) ──
    capped = min(raw_score, 90)
    scaled = int(60 + (capped / 90) * 35)
    return min(scaled, 95)


# ── Public method ──────────────────────────────────────────────────────────────

def find_matches(project_id: str) -> List[Dict[str, Any]]:
    """
    Bước 2 — Tìm danh sách chuyên gia phù hợp cho một Project.

    Logic:
        1. Lấy Project theo ID.
        2. Lấy toàn bộ Expert đang available (is_available=True).
        3. Tính điểm tương thích cho từng Expert.
        4. Lọc Expert có score > 0.
        5. Sắp xếp theo score giảm dần.

    Args:
        project_id: ID của Project cần tìm chuyên gia.

    Returns:
        List[dict] sắp xếp theo score giảm dần. Mỗi phần tử:
        {
            "expert"        : dict (expert.to_dict()),
            "score"         : int  (60–95),
            "score_label"   : str  (vd: "87%"),
            "match_reasons" : list (các specialty đã khớp)
        }

    Raises:
        LookupError: Nếu không tìm thấy Project.
        ValueError : Nếu Project chưa ở trạng thái Pending.
    """
    # ── Lấy Project ───────────────────────────────────────────────────
    project = _project_repo.get_by_id(project_id)
    if not project:
        raise LookupError(f"Không tìm thấy Project với id='{project_id}'.")

    # Project phải đang ở Pending mới cần tìm matching
    if project.status not in ("Pending", "Negotiating"):
        raise ValueError(
            f"Project id='{project_id}' đang ở status='{project.status}'. "
            "Chỉ có thể matching khi status là Pending hoặc Negotiating."
        )

    # ── Lấy danh sách Expert available ────────────────────────────────
    available_experts = _expert_repo.get_available()
    if not available_experts:
        logger.warning(
            "[MatchingService] Không có Expert nào available cho project='%s'.",
            project_id,
        )
        return []

    # ── Tính điểm và lọc ──────────────────────────────────────────────
    results = []
    for expert in available_experts:
        score = _calculate_match_score(project, expert)
        if score == 0:
            continue

        # Ghi lại các specialty đã khớp để trả về cho client
        match_reasons = [
            req for req in project.required_specialties
            if any(
                req.lower() in spec.lower() or spec.lower() in req.lower()
                for spec in expert.specialties
            )
        ]

        results.append({
            "expert": expert.to_dict(),
            "score": score,
            "score_label": f"{score}%",
            "match_reasons": match_reasons,
        })

    # ── Sắp xếp theo score giảm dần ───────────────────────────────────
    results.sort(key=lambda x: x["score"], reverse=True)

    logger.info(
        "[MatchingService] Project id='%s' — tìm được %d chuyên gia phù hợp.",
        project_id, len(results),
    )
    return results