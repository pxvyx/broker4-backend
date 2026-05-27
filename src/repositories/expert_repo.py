"""
Module  : src/repositories/expert_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : ExpertRepository — toàn bộ thao tác đọc/ghi dữ liệu Expert.

Nguyên tắc tầng Repository:
  - Chỉ trả về Model objects (Expert) hoặc None / [].
  - KHÔNG chứa business logic matching hay scoring.
  - KHÔNG biết gì về HTTP, Flask, hay JSON response format.
  - Tầng Services ở trên gọi Repository, chiều ngược lại KHÔNG được phép.
"""

import logging
from typing import List, Optional

from src.models.expert import Expert
from src.repositories.json_repository import JsonRepository

logger = logging.getLogger(__name__)

# Đường dẫn tương đối tính từ thư mục gốc broker_4_0_backend/
_EXPERT_DATA_FILE = "data/experts.json"


class ExpertRepository(JsonRepository):
    """
    Repository chuyên biệt cho entity Expert.
    Kế thừa JsonRepository để dùng read_json / write_json làm primitive I/O.
    """

    def __init__(self, filepath: str = _EXPERT_DATA_FILE):
        """
        Args:
            filepath: Đường dẫn tương đối đến file experts.json.
                      Mặc định: "data/experts.json" (tính từ broker_4_0_backend/).
                      Có thể override khi test để trỏ vào file fixture.
        """
        super().__init__(filepath)

    # ------------------------------------------------------------------
    # Private helpers — chỉ dùng nội bộ trong class này
    # ------------------------------------------------------------------

    def _load_all_raw(self) -> List[dict]:
        """Đọc toàn bộ file, trả về list[dict] thô. Dùng nội bộ."""
        return self.read_json()

    def _save_all_raw(self, raw_list: List[dict]) -> bool:
        """Ghi toàn bộ list[dict] thô xuống file. Dùng nội bộ."""
        return self.write_json(raw_list)

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def get_all(self) -> List[Expert]:
        """
        Lấy toàn bộ danh sách Expert dưới dạng Model objects.

        Các record lỗi cấu trúc bị bỏ qua và log, không ảnh hưởng các record còn lại.

        Returns:
            List[Expert] — Có thể là [] nếu file lỗi hoặc rỗng.
        """
        raw_list = self._load_all_raw()
        result: List[Expert] = []

        for raw in raw_list:
            try:
                result.append(Expert.from_dict(raw))
            except (KeyError, TypeError) as exc:
                logger.warning(
                    "[ExpertRepository.get_all] Bỏ qua record lỗi cấu trúc "
                    "(id='%s'): %s",
                    raw.get("id", "UNKNOWN"),
                    str(exc),
                )

        return result

    def get_by_id(self, expert_id: str) -> Optional[Expert]:
        """
        Tìm và trả về một Expert theo ID.

        Args:
            expert_id: Chuỗi định danh Expert (vd: "EXP-001").

        Returns:
            Expert object nếu tìm thấy và parse thành công.
            None nếu không tìm thấy hoặc record bị lỗi cấu trúc.
        """
        raw_list = self._load_all_raw()

        for raw in raw_list:
            if raw.get("id") == expert_id:
                try:
                    return Expert.from_dict(raw)
                except (KeyError, TypeError) as exc:
                    logger.error(
                        "[ExpertRepository.get_by_id] Tìm thấy id='%s' "
                        "nhưng parse thất bại: %s",
                        expert_id,
                        str(exc),
                    )
                    return None

        logger.debug(
            "[ExpertRepository.get_by_id] Không tìm thấy Expert với id='%s'.",
            expert_id,
        )
        return None

    def get_by_specialty(self, specialty: str) -> List[Expert]:
        """
        Lọc Expert theo chuyên môn trong trường `specialties`.
        Đây là phương thức cốt lõi phục vụ luồng matching A1 và A2.

        Tìm kiếm substring, không phân biệt hoa/thường (case-insensitive).

        Args:
            specialty: Từ khóa chuyên môn (vd: "Machine Learning", "AI", "sinh học").

        Returns:
            List[Expert] có ít nhất một specialty chứa từ khóa.
        """
        keyword = specialty.lower().strip()
        return [
            expert for expert in self.get_all()
            if any(keyword in s.lower() for s in expert.specialties)
        ]

    def get_available(self) -> List[Expert]:
        """
        Lọc danh sách Expert đang sẵn sàng nhận dự án (is_available=True).
        Dùng làm bước tiền lọc trước khi matching chuyên môn.

        Returns:
            List[Expert] với is_available == True.
        """
        return [exp for exp in self.get_all() if exp.is_available]

    def get_by_technology(self, technology: str) -> List[Expert]:
        """
        Lọc Expert theo công nghệ trong trường `available_technologies`.
        Tìm kiếm substring, không phân biệt hoa/thường.

        Args:
            technology: Tên công nghệ (vd: "PyTorch", "Blockchain", "ERP").

        Returns:
            List[Expert] sở hữu ít nhất một công nghệ khớp với từ khóa.
        """
        keyword = technology.lower().strip()
        return [
            expert for expert in self.get_all()
            if any(keyword in t.lower() for t in expert.available_technologies)
        ]

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def update_availability(
        self,
        expert_id: str,
        is_available: bool,
    ) -> bool:
        """
        Cập nhật trạng thái sẵn sàng nhận dự án của Expert.
        Được gọi bởi tầng Service khi Expert được assign hoặc hoàn thành dự án.

        Args:
            expert_id:    ID của Expert cần cập nhật.
            is_available: True = rảnh, sẵn sàng nhận dự án mới.
                          False = đang bận, không nhận thêm.

        Returns:
            True nếu cập nhật và ghi file thành công.
            False nếu không tìm thấy Expert hoặc ghi file thất bại.
        """
        raw_list = self._load_all_raw()

        target_index: Optional[int] = next(
            (i for i, r in enumerate(raw_list) if r.get("id") == expert_id),
            None,
        )

        if target_index is None:
            logger.warning(
                "[ExpertRepository.update_availability] "
                "Không tìm thấy Expert id='%s'. Bỏ qua cập nhật.",
                expert_id,
            )
            return False

        raw_list[target_index]["is_available"] = is_available
        logger.info(
            "[ExpertRepository.update_availability] "
            "Expert id='%s' → is_available=%s.",
            expert_id,
            is_available,
        )
        return self._save_all_raw(raw_list)

    def save(self, expert: Expert) -> bool:
        """
        Lưu một Expert object xuống file (thêm mới hoặc cập nhật toàn bộ record).

        Logic upsert:
            · id đã tồn tại → replace toàn bộ record.
            · id chưa có    → append vào cuối file.

        Args:
            expert: Expert object cần lưu (đã được validate ở tầng Service).

        Returns:
            True nếu ghi thành công, False nếu thất bại.
        """
        raw_list = self._load_all_raw()
        expert_dict = expert.to_dict()

        target_index: Optional[int] = next(
            (i for i, r in enumerate(raw_list) if r.get("id") == expert.id),
            None,
        )

        if target_index is not None:
            raw_list[target_index] = expert_dict
            logger.info(
                "[ExpertRepository.save] Cập nhật Expert id='%s'.", expert.id
            )
        else:
            raw_list.append(expert_dict)
            logger.info(
                "[ExpertRepository.save] Thêm mới Expert id='%s'.", expert.id
            )

        return self._save_all_raw(raw_list)