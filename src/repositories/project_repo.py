"""
Module  : src/repositories/project_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : ProjectRepository — toàn bộ thao tác đọc/ghi dữ liệu Project
          trên MongoDB Atlas.

THAY ĐỔI SO VỚI PHIÊN BẢN CŨ (JSON):
    ① Không còn kế thừa JsonRepository — kết nối thẳng đến MongoDB.
    ② Dùng collection.find() / find_one() thay cho vòng lặp Python.
    ③ Dùng update_one(..., upsert=True) thay cho đọc-sửa-ghi toàn bộ file.
    ④ Loại bỏ trường _id (ObjectId) của MongoDB trước khi map vào Model.

Thiết kế ID:
    - MongoDB tự tạo _id (ObjectId) cho mỗi document — dùng nội bộ.
    - Ứng dụng dùng trường "id" dạng string (vd: "PRJ-A1B2C3D4") — bất biến.
    - Frontend và các tầng trên KHÔNG BAO GIỜ thấy _id.

Collection: broker4_db.projects
Index nên tạo trên Atlas:
    db.projects.createIndex({ "id": 1 }, { unique: true })
    db.projects.createIndex({ "sme_id": 1 })
    db.projects.createIndex({ "status": 1 })
"""

import logging
from typing import List, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.config.db import get_db
from src.models.project import Project

logger = logging.getLogger(__name__)

# Projection dùng chung: yêu cầu MongoDB KHÔNG trả về trường _id
# → tiết kiệm băng thông, tránh lỗi ObjectId khi truyền vào from_dict()
_NO_ID: dict = {"_id": 0}


class ProjectRepository:
    """
    Repository chuyên biệt cho entity Project trên MongoDB Atlas.

    Mọi thao tác đọc đều dùng MongoDB query (find/find_one) thay vì
    tải toàn bộ collection về RAM và lọc bằng Python.
    """

    def __init__(self) -> None:
        """
        Khởi tạo repository bằng cách lấy collection 'projects'
        từ database 'broker4_db' thông qua get_db() (Singleton).
        """
        self.collection: Collection = get_db()["projects"]

    # ------------------------------------------------------------------
    # Private helper
    # ------------------------------------------------------------------

    def _doc_to_project(self, doc: dict) -> Optional[Project]:
        """
        Chuyển một MongoDB document (đã loại bỏ _id) thành Project object.

        Args:
            doc: dict trả về từ find() hoặc find_one(), KHÔNG có trường _id.

        Returns:
            Project object, hoặc None nếu document thiếu field bắt buộc.
        """
        try:
            return Project.from_dict(doc)
        except (KeyError, TypeError) as exc:
            logger.warning(
                "[ProjectRepository] Bỏ qua document lỗi cấu trúc (id='%s'): %s",
                doc.get("id", "UNKNOWN"), str(exc),
            )
            return None

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def get_all(self) -> List[Project]:
        """
        Lấy toàn bộ danh sách Project từ collection.

        MongoDB query: db.projects.find({}, {"_id": 0})

        Returns:
            List[Project] — [] nếu collection rỗng hoặc lỗi kết nối.
        """
        try:
            cursor = self.collection.find({}, _NO_ID)
            result = [
                project
                for doc in cursor
                if (project := self._doc_to_project(doc)) is not None
            ]
            logger.debug(
                "[ProjectRepository.get_all] Lấy được %d project(s).", len(result)
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ProjectRepository.get_all] Lỗi MongoDB: %s. Trả về [].", str(exc)
            )
            return []

    def get_by_id(self, project_id: str) -> Optional[Project]:
        """
        Tìm một Project theo trường 'id' (string ID của ứng dụng, không phải _id).

        MongoDB query: db.projects.find_one({"id": project_id}, {"_id": 0})

        Args:
            project_id: String ID dạng "PRJ-XXXXXXXX".

        Returns:
            Project object nếu tìm thấy, None nếu không có hoặc lỗi.
        """
        try:
            doc = self.collection.find_one({"id": project_id}, _NO_ID)
            if doc is None:
                logger.debug(
                    "[ProjectRepository.get_by_id] Không tìm thấy id='%s'.",
                    project_id,
                )
                return None
            return self._doc_to_project(doc)

        except PyMongoError as exc:
            logger.error(
                "[ProjectRepository.get_by_id] Lỗi MongoDB khi tìm id='%s': %s.",
                project_id, str(exc),
            )
            return None

    def get_by_sme_id(self, sme_id: str) -> List[Project]:
        """
        Lấy toàn bộ Project thuộc về một SME.

        MongoDB query: db.projects.find({"sme_id": sme_id}, {"_id": 0})
        Tương đương SQL: SELECT * FROM projects WHERE sme_id = ?

        Args:
            sme_id: ID của SME cần truy vấn (vd: "SME-001").

        Returns:
            List[Project] của SME đó. [] nếu không có hoặc lỗi.
        """
        try:
            cursor = self.collection.find({"sme_id": sme_id}, _NO_ID)
            result = [
                project
                for doc in cursor
                if (project := self._doc_to_project(doc)) is not None
            ]
            logger.debug(
                "[ProjectRepository.get_by_sme_id] sme_id='%s' → %d project(s).",
                sme_id, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ProjectRepository.get_by_sme_id] Lỗi MongoDB (sme_id='%s'): %s.",
                sme_id, str(exc),
            )
            return []

    def get_by_status(self, status: str) -> List[Project]:
        """
        Lọc Project theo trạng thái.

        MongoDB query: db.projects.find({"status": status}, {"_id": 0})
        Tương đương SQL: SELECT * FROM projects WHERE status = ?

        Args:
            status: Một trong Pending | Negotiating | In Progress | Completed.

        Returns:
            List[Project] khớp status. [] nếu không có hoặc lỗi.
        """
        try:
            cursor = self.collection.find({"status": status}, _NO_ID)
            result = [
                project
                for doc in cursor
                if (project := self._doc_to_project(doc)) is not None
            ]
            logger.debug(
                "[ProjectRepository.get_by_status] status='%s' → %d project(s).",
                status, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ProjectRepository.get_by_status] Lỗi MongoDB (status='%s'): %s.",
                status, str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, project: Project) -> bool:
        """
        Upsert một Project vào MongoDB.

        MongoDB operation:
            db.projects.update_one(
                {"id": project.id},          ← filter: tìm document có id này
                {"$set": project.to_dict()}, ← update: ghi đè toàn bộ fields
                upsert=True                  ← nếu không tìm thấy → insert mới
            )

        Hành vi:
            - Document đã tồn tại (matched_count = 1) → cập nhật toàn bộ fields.
            - Document chưa có   (upserted_id  ≠ None) → tạo document mới.
            - MongoDB tự tạo _id (ObjectId) khi insert — ứng dụng không cần quan tâm.

        Args:
            project: Project object đã được validate ở tầng Service.

        Returns:
            True  — Upsert thành công (dù là insert hay update).
            False — Lỗi PyMongo, hệ thống tiếp tục chạy (đã được log).
        """
        try:
            result = self.collection.update_one(
                filter={"id": project.id},
                update={"$set": project.to_dict()},
                upsert=True,
            )

            if result.upserted_id is not None:
                logger.info(
                    "[ProjectRepository.save] INSERT mới — Project id='%s'.",
                    project.id,
                )
            else:
                logger.info(
                    "[ProjectRepository.save] UPDATE — Project id='%s' "
                    "(%d field(s) thay đổi).",
                    project.id, result.modified_count,
                )
            return True

        except PyMongoError as exc:
            logger.error(
                "[ProjectRepository.save] Lỗi MongoDB khi upsert id='%s': %s.",
                project.id, str(exc),
            )
            return False