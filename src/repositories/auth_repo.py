"""
Module  : src/repositories/auth_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : AuthRepository — tra cứu và tạo mới Profile người dùng trên MongoDB.

Thiết kế đa-collection:
    SME     → collection: smes     (id prefix: "SME-")
    Expert  → collection: experts  (id prefix: "EXP-")

    Hàm find_by_email() tìm tuần tự: smes → experts.
    Inject thêm trường "role" vào dict trả về để Service và Controller
    phân biệt loại tài khoản mà không cần query thêm.

Quy ước _NO_ID:
    Mọi query find đều dùng {"_id": 0} — tuyệt đối không để ObjectId
    lộ ra ngoài tầng Repository.

Index nên tạo trên Atlas:
    db.smes.createIndex(    { "email": 1 }, { unique: true })
    db.experts.createIndex( { "email": 1 }, { unique: true })
    db.smes.createIndex(    { "firebase_uid": 1 }, { unique: true })
    db.experts.createIndex( { "firebase_uid": 1 }, { unique: true })
"""

import logging
from typing import Optional

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from src.config.db import get_db

logger = logging.getLogger(__name__)

# Loại bỏ _id (ObjectId) khỏi mọi kết quả trả về
_NO_ID: dict = {"_id": 0}


class AuthRepository:
    """
    Repository xử lý tra cứu và tạo mới Profile người dùng.
    Làm việc với 2 collection: smes và experts.
    """

    def __init__(self) -> None:
        db = get_db()
        self.sme_collection: Collection = db["smes"]
        self.expert_collection: Collection = db["experts"]

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def find_by_email(self, email: str) -> Optional[dict]:
        """
        Tìm Profile người dùng theo email — tra cứu tuần tự SME → Expert.

        Logic:
            1. Tìm trong collection `smes` trước.
            2. Nếu thấy → inject {"role": "SME"} → trả về ngay.
            3. Nếu không → tìm trong collection `experts`.
            4. Nếu thấy → inject {"role": "EXPERT"} → trả về.
            5. Không thấy ở đâu → trả về None.

        Trường "role" được inject tại đây để tầng Service không cần
        biết document đến từ collection nào.

        Args:
            email: Địa chỉ email cần tìm (lấy từ Firebase decoded token).

        Returns:
            dict Profile kèm trường "role", hoặc None nếu chưa tồn tại.
        """
        email = email.lower().strip()

        try:
            # ── Tìm trong SMEs ─────────────────────────────────────────
            sme_doc = self.sme_collection.find_one({"email": email}, _NO_ID)
            if sme_doc is not None:
                sme_doc["role"] = "SME"
                logger.debug(
                    "[AuthRepository.find_by_email] Tìm thấy SME với email='%s'.",
                    email,
                )
                return sme_doc

            # ── Tìm trong Experts ──────────────────────────────────────
            expert_doc = self.expert_collection.find_one({"email": email}, _NO_ID)
            if expert_doc is not None:
                expert_doc["role"] = "EXPERT"
                logger.debug(
                    "[AuthRepository.find_by_email] Tìm thấy Expert với email='%s'.",
                    email,
                )
                return expert_doc

            # ── Không tìm thấy ─────────────────────────────────────────
            logger.debug(
                "[AuthRepository.find_by_email] Không tìm thấy email='%s' "
                "trong cả smes lẫn experts.", email,
            )
            return None

        except PyMongoError as exc:
            logger.error(
                "[AuthRepository.find_by_email] Lỗi MongoDB (email='%s'): %s.",
                email, str(exc),
            )
            return None

    def find_by_uid(self, firebase_uid: str) -> Optional[dict]:
        """
        Tìm Profile người dùng theo Firebase UID — tra cứu tuần tự SME → Expert.

        Dùng sau khi đã xác minh token để lấy profile đầy đủ.

        Args:
            firebase_uid: UID từ Firebase decoded token.

        Returns:
            dict Profile kèm trường "role", hoặc None nếu chưa tồn tại.
        """
        try:
            sme_doc = self.sme_collection.find_one(
                {"firebase_uid": firebase_uid}, _NO_ID
            )
            if sme_doc is not None:
                sme_doc["role"] = "SME"
                return sme_doc

            expert_doc = self.expert_collection.find_one(
                {"firebase_uid": firebase_uid}, _NO_ID
            )
            if expert_doc is not None:
                expert_doc["role"] = "EXPERT"
                return expert_doc

            return None

        except PyMongoError as exc:
            logger.error(
                "[AuthRepository.find_by_uid] Lỗi MongoDB (uid='%s'): %s.",
                firebase_uid, str(exc),
            )
            return None

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def create_sme(self, sme_dict: dict) -> None:
        """
        Tạo mới một SME document trong collection `smes`.

        Args:
            sme_dict: dict đầy đủ từ Service, đã có id, firebase_uid, email...

        Raises:
            DuplicateKeyError: Nếu email hoặc firebase_uid đã tồn tại.
            PyMongoError     : Lỗi kết nối hoặc ghi MongoDB.
        """
        try:
            self.sme_collection.insert_one(sme_dict)
            logger.info(
                "[AuthRepository.create_sme] INSERT SME id='%s' — email='%s'.",
                sme_dict.get("id"), sme_dict.get("email"),
            )
        except DuplicateKeyError as exc:
            logger.warning(
                "[AuthRepository.create_sme] Duplicate key — "
                "email='%s' đã tồn tại: %s", sme_dict.get("email"), str(exc),
            )
            raise

        except PyMongoError as exc:
            logger.error(
                "[AuthRepository.create_sme] Lỗi MongoDB: %s", str(exc)
            )
            raise

    def create_expert(self, expert_dict: dict) -> None:
        """
        Tạo mới một Expert document trong collection `experts`.

        Args:
            expert_dict: dict đầy đủ từ Service, đã có id, firebase_uid, email...

        Raises:
            DuplicateKeyError: Nếu email hoặc firebase_uid đã tồn tại.
            PyMongoError     : Lỗi kết nối hoặc ghi MongoDB.
        """
        try:
            self.expert_collection.insert_one(expert_dict)
            logger.info(
                "[AuthRepository.create_expert] INSERT Expert id='%s' — email='%s'.",
                expert_dict.get("id"), expert_dict.get("email"),
            )
        except DuplicateKeyError as exc:
            logger.warning(
                "[AuthRepository.create_expert] Duplicate key — "
                "email='%s' đã tồn tại: %s", expert_dict.get("email"), str(exc),
            )
            raise

        except PyMongoError as exc:
            logger.error(
                "[AuthRepository.create_expert] Lỗi MongoDB: %s", str(exc)
            )
            raise