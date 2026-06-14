"""
Module  : src/repositories/milestone_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : MilestoneRepository — toàn bộ thao tác đọc/ghi Milestone trên MongoDB.

Milestone là các mốc tiến độ trong quá trình thực hiện dự án (Bước 5).
Mỗi Project có nhiều Milestone — quan hệ: Project (1) ──< Milestone (N).

Suy luận cấu trúc từ MilestoneRepository cũ và ngữ cảnh Broker 4.0:
    id           : str  — định danh duy nhất (vd: "MST-A1B2C3D4")
    project_id   : str  — khóa ngoại → Project.id
    title        : str  — tên mốc (vd: "Hoàn thành thiết kế hệ thống")
    description  : str  — mô tả chi tiết (tuỳ chọn)
    due_date     : str  — hạn hoàn thành YYYY-MM-DD (tuỳ chọn)
    status       : str  — Pending | In Progress | Completed
    completion_percentage : int — % hoàn thành (0–100)
    created_at   : str  — ngày tạo YYYY-MM-DD

Collection: broker4_db.milestones
Index nên tạo:
    db.milestones.createIndex({ "id": 1 },          { unique: true })
    db.milestones.createIndex({ "project_id": 1 })
    db.milestones.createIndex({ "status": 1 })
"""

import logging
from typing import List, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.config.db import get_db
from src.models.milestone import Milestone

logger = logging.getLogger(__name__)

_NO_ID: dict = {"_id": 0}


class MilestoneRepository:
    """
    Repository chuyên biệt cho entity Milestone trên MongoDB Atlas.

    Không kế thừa JsonRepository — kết nối thẳng đến MongoDB
    thông qua get_db() (Singleton từ src/config/db.py).
    """

    def __init__(self) -> None:
        self.collection: Collection = get_db()["milestones"]

    # ------------------------------------------------------------------
    # Private helper
    # ------------------------------------------------------------------

    def _doc_to_milestone(self, doc: dict) -> Optional[Milestone]:
        """
        Chuyển MongoDB document thành Milestone object.
        Loại bỏ _id (ObjectId) trước khi parse để tránh lỗi Model.
        """
        doc.pop("_id", None)
        try:
            return Milestone.from_dict(doc)
        except (KeyError, TypeError) as exc:
            logger.warning(
                "[MilestoneRepository] Bỏ qua document lỗi cấu trúc (id='%s'): %s",
                doc.get("id", "UNKNOWN"), str(exc),
            )
            return None

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def get_all(self) -> List[Milestone]:
        """
        Lấy toàn bộ danh sách Milestone.

        MongoDB: db.milestones.find({}, {"_id": 0})
        """
        try:
            cursor = self.collection.find({}, _NO_ID)
            result = [
                milestone
                for doc in cursor
                if (milestone := self._doc_to_milestone(doc)) is not None
            ]
            logger.debug(
                "[MilestoneRepository.get_all] Lấy được %d milestone(s).",
                len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[MilestoneRepository.get_all] Lỗi MongoDB: %s. Trả về [].",
                str(exc),
            )
            return []

    def get_by_id(self, milestone_id: str) -> Optional[Milestone]:
        """
        Tìm Milestone theo string ID.

        MongoDB: db.milestones.find_one({"id": milestone_id}, {"_id": 0})

        Args:
            milestone_id: String ID dạng "MST-XXXXXXXX".

        Returns:
            Milestone object nếu tìm thấy, None nếu không có hoặc lỗi.
        """
        try:
            doc = self.collection.find_one({"id": milestone_id}, _NO_ID)
            if doc is None:
                logger.debug(
                    "[MilestoneRepository.get_by_id] "
                    "Không tìm thấy id='%s'.", milestone_id,
                )
                return None
            return self._doc_to_milestone(doc)

        except PyMongoError as exc:
            logger.error(
                "[MilestoneRepository.get_by_id] Lỗi MongoDB (id='%s'): %s.",
                milestone_id, str(exc),
            )
            return None

    def get_by_project_id(self, project_id: str) -> List[Milestone]:
        """
        Lấy toàn bộ Milestone của một Project, sắp xếp theo due_date tăng dần.

        MongoDB:
            db.milestones.find(
                {"project_id": project_id},
                {"_id": 0}
            ).sort("due_date", 1)

        Tương đương SQL:
            SELECT * FROM milestones
            WHERE project_id = ?
            ORDER BY due_date ASC

        Args:
            project_id: ID của Project cần lấy milestones.

        Returns:
            List[Milestone] đã sắp xếp theo due_date. [] nếu không có hoặc lỗi.
        """
        try:
            cursor = self.collection.find(
                {"project_id": project_id}, _NO_ID
            ).sort("due_date", 1)   # 1 = ascending

            result = [
                milestone
                for doc in cursor
                if (milestone := self._doc_to_milestone(doc)) is not None
            ]
            logger.debug(
                "[MilestoneRepository.get_by_project_id] "
                "project_id='%s' → %d milestone(s).",
                project_id, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[MilestoneRepository.get_by_project_id] "
                "Lỗi MongoDB (project_id='%s'): %s.", project_id, str(exc),
            )
            return []

    def get_by_status(self, status: str) -> List[Milestone]:
        """
        Lọc Milestone theo trạng thái.

        MongoDB: db.milestones.find({"status": status}, {"_id": 0})

        Args:
            status: Một trong Pending | In Progress | Completed.
        """
        try:
            cursor = self.collection.find({"status": status}, _NO_ID)
            result = [
                milestone
                for doc in cursor
                if (milestone := self._doc_to_milestone(doc)) is not None
            ]
            logger.debug(
                "[MilestoneRepository.get_by_status] "
                "status='%s' → %d milestone(s).",
                status, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[MilestoneRepository.get_by_status] "
                "Lỗi MongoDB (status='%s'): %s.", status, str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, milestone: Milestone) -> bool:
        """
        Upsert Milestone: tìm theo "id" → cập nhật hoặc tạo mới.

        MongoDB:
            db.milestones.update_one(
                {"id": milestone.id},
                {"$set": milestone.to_dict()},
                upsert=True
            )

        Args:
            milestone: Milestone object đã được validate ở tầng Service.

        Returns:
            True — Upsert thành công. False — Lỗi PyMongo.
        """
        try:
            result = self.collection.update_one(
                {"id": milestone.id},
                {"$set": milestone.to_dict()},
                upsert=True,
            )

            if result.upserted_id is not None:
                logger.info(
                    "[MilestoneRepository.save] INSERT mới — "
                    "Milestone id='%s' (project='%s').",
                    milestone.id, milestone.project_id,
                )
            else:
                logger.info(
                    "[MilestoneRepository.save] UPDATE — Milestone id='%s'.",
                    milestone.id,
                )
            return True

        except PyMongoError as exc:
            logger.error(
                "[MilestoneRepository.save] Lỗi MongoDB (id='%s'): %s.",
                milestone.id, str(exc),
            )
            return False