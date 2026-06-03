import logging
from src.repositories.expert_repo import ExpertRepository

logger = logging.getLogger(__name__)
_expert_repo = ExpertRepository()

def get_all_experts() -> list:
    """
    Lấy danh sách toàn bộ chuyên gia từ database/file JSON.
    """
    try:
        # Giả định ExpertRepository đã có sẵn hàm get_all() đọc từ JSON
        experts = _expert_repo.get_all()
        logger.info(f"[ExpertService] Lấy thành công {len(experts)} chuyên gia.")
        return experts
    except Exception as e:
        logger.error(f"[ExpertService] Lỗi khi lấy danh sách chuyên gia: {str(e)}")
        raise e