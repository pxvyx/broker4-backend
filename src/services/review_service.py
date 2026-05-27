"""
Module  : src/services/review_service.py
Layer   : Services (Business Logic)
Purpose : Xử lý nghiệp vụ Đánh giá sau dự án.

Luồng 7 bước — phụ trách:
    Bước 6 — Đánh giá: submit_review() → Review + Project(status="Completed")
                        + Cập nhật rating trung bình của Expert.
    Bước 7 — Knowledge Graph: dữ liệu Review là đầu vào (xử lý sau).
"""

import logging
import uuid
from datetime import date
from typing import Optional

from src.models.review import Review
from src.repositories.review_repo import ReviewRepository
from src.repositories.project_repo import ProjectRepository
from src.repositories.expert_repo import ExpertRepository

logger = logging.getLogger(__name__)

_review_repo = ReviewRepository()
_project_repo = ProjectRepository()
_expert_repo = ExpertRepository()


def submit_review(
    project_id: str,
    reviewer_sme_id: str,
    reviewed_expert_id: str,
    rating: int,
    feedback: str,
    tags: Optional[list] = None,
) -> Review:
    """
    Bước 6 — SME gửi đánh giá sau khi Project hoàn tất.

    Thực hiện 3 thao tác theo thứ tự:
        1. Tạo và lưu Review mới.
        2. Chuyển Project → status="Completed".
        3. Tính lại rating trung bình của Expert từ toàn bộ reviews.

    Args:
        project_id          : ID của Project vừa hoàn thành.
        reviewer_sme_id     : ID của SME gửi đánh giá.
        reviewed_expert_id  : ID của Expert được đánh giá.
        rating              : Điểm đánh giá từ 1 đến 5.
        feedback            : Nhận xét chi tiết bằng văn bản.
        tags                : Nhãn phân loại (vd: ["đúng tiến độ", "chuyên nghiệp"]).

    Returns:
        Review object vừa được lưu thành công.

    Raises:
        LookupError: Nếu Project không tồn tại.
        ValueError : Nếu rating ngoài khoảng [1, 5],
                     hoặc Project không ở trạng thái hợp lệ để đánh giá.
        IOError    : Nếu ghi dữ liệu thất bại.
    """
    # ── Validate rating ────────────────────────────────────────────────
    rating = int(rating)
    if not (1 <= rating <= 5):
        raise ValueError(f"rating phải là số nguyên từ 1 đến 5. Nhận được: {rating}.")

    if not feedback or not feedback.strip():
        raise ValueError("feedback không được để trống.")

    # ── Validate Project ───────────────────────────────────────────────
    project = _project_repo.get_by_id(project_id)
    if not project:
        raise LookupError(f"Không tìm thấy Project với id='{project_id}'.")
    if project.status not in ("In Progress", "Completed"):
        raise ValueError(
            f"Project id='{project_id}' đang ở status='{project.status}'. "
            "Chỉ có thể đánh giá khi Project đang In Progress hoặc Completed."
        )

    # ── Tạo Review mới ────────────────────────────────────────────────
    review = Review(
        id=f"RVW-{uuid.uuid4().hex[:8].upper()}",
        project_id=project_id,
        reviewer_sme_id=reviewer_sme_id,
        reviewed_expert_id=reviewed_expert_id,
        rating=rating,
        feedback=feedback.strip(),
        created_at=date.today().isoformat(),
        tags=tags or [],
    )

    if not _review_repo.save(review):
        raise IOError("Lỗi hệ thống: Không thể lưu Review vào database.")

    # ── Chuyển Project → Completed ─────────────────────────────────────
    if project.status != "Completed":
        project.status = "Completed"
        if not _project_repo.save(project):
            logger.warning(
                "[ReviewService] Đã lưu Review nhưng không cập nhật được "
                "status của Project id='%s'.", project_id,
            )
        else:
            logger.info(
                "[ReviewService] Project id='%s' → Completed.", project_id
            )

    # ── Tính lại rating trung bình cho Expert ─────────────────────────
    _recalculate_expert_rating(reviewed_expert_id)

    logger.info(
        "[ReviewService] Review id='%s' — Project='%s' — Expert='%s' — rating=%d.",
        review.id, project_id, reviewed_expert_id, rating,
    )
    return review


# ── Private helper ─────────────────────────────────────────────────────────────

def _recalculate_expert_rating(expert_id: str) -> None:
    """
    Tính lại điểm rating trung bình của Expert từ toàn bộ Reviews đã nhận.
    Được gọi sau mỗi lần submit_review() để đảm bảo dữ liệu nhất quán.

    Args:
        expert_id: ID của Expert cần cập nhật rating.
    """
    expert = _expert_repo.get_by_id(expert_id)
    if not expert:
        logger.warning(
            "[ReviewService._recalculate_expert_rating] "
            "Không tìm thấy Expert id='%s'. Bỏ qua cập nhật rating.",
            expert_id,
        )
        return

    all_reviews = _review_repo.get_by_expert_id(expert_id)
    if not all_reviews:
        return

    avg_rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 2)
    expert.rating = avg_rating

    if _expert_repo.save(expert):
        logger.info(
            "[ReviewService._recalculate_expert_rating] "
            "Expert id='%s' — rating mới: %.2f (từ %d review).",
            expert_id, avg_rating, len(all_reviews),
        )