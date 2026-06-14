"""
Module  : src/repositories/post_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : PostRepository — toàn bộ thao tác đọc/ghi Post trên MongoDB Atlas.

Nguyên tắc tầng Repository:
    - Chỉ trả về dict hoặc List[dict] (không parse thành Model ở đây).
      Lý do: get_recent_posts() trả thẳng dict để Service linh hoạt xử lý.
    - KHÔNG chứa business logic.
    - Mọi thao tác atomic (toggle_like, add_comment) dùng MongoDB operators
      ($addToSet, $pull, $push) — đảm bảo thread-safe, không race condition.
    - _NO_ID loại bỏ _id (ObjectId) khỏi MỌI kết quả trả về.

Collection: broker4_db.posts
Index nên tạo trên Atlas:
    db.posts.createIndex({ "id": 1 },         { unique: true })
    db.posts.createIndex({ "created_at": -1 }) ← tối ưu sort feed mới nhất
    db.posts.createIndex({ "author_id": 1 })
"""

import logging
from typing import List, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.config.db import get_db

logger = logging.getLogger(__name__)

# Loại bỏ _id khỏi MỌI kết quả trả về — tuyệt đối không để _id lộ ra ngoài
_NO_ID: dict = {"_id": 0}


class PostRepository:
    """
    Repository chuyên biệt cho entity Post trên MongoDB Atlas.

    Sử dụng MongoDB atomic operators cho các thao tác like/comment
    để đảm bảo tính nhất quán trong môi trường concurrent.
    """

    def __init__(self) -> None:
        self.collection: Collection = get_db()["posts"]

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def get_recent_posts(self, limit: int = 50) -> List[dict]:
        """
        Lấy danh sách bài viết mới nhất, sắp xếp theo thời gian tạo giảm dần.

        MongoDB:
            db.posts.find({}, {"_id": 0})
                    .sort("created_at", -1)
                    .limit(limit)

        Args:
            limit: Số lượng bài viết tối đa cần lấy (mặc định 50).

        Returns:
            List[dict] — mỗi dict là một post document đầy đủ (kể cả likes, comments).
            [] nếu collection rỗng hoặc lỗi kết nối.
        """
        try:
            cursor = (
                self.collection
                .find({}, _NO_ID)
                .sort("created_at", -1)
                .limit(limit)
            )
            result = list(cursor)
            logger.debug(
                "[PostRepository.get_recent_posts] Lấy được %d post(s) "
                "(limit=%d).", len(result), limit,
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[PostRepository.get_recent_posts] Lỗi MongoDB: %s. Trả về [].",
                str(exc),
            )
            return []

    def get_by_id(self, post_id: str) -> Optional[dict]:
        """
        Tìm một Post theo string ID.

        MongoDB: db.posts.find_one({"id": post_id}, {"_id": 0})

        Args:
            post_id: String ID dạng "POST-XXXXXXXX".

        Returns:
            dict nếu tìm thấy, None nếu không có hoặc lỗi.
        """
        try:
            doc = self.collection.find_one({"id": post_id}, _NO_ID)
            if doc is None:
                logger.debug(
                    "[PostRepository.get_by_id] Không tìm thấy id='%s'.", post_id
                )
            return doc

        except PyMongoError as exc:
            logger.error(
                "[PostRepository.get_by_id] Lỗi MongoDB (id='%s'): %s.",
                post_id, str(exc),
            )
            return None

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, post_dict: dict) -> None:
        """
        Tạo mới một Post document trong collection.
        Dùng insert_one() — Post ID do tầng Service sinh ra, không cần upsert.

        Args:
            post_dict: dict đầy đủ từ Post.to_dict() — đã có trường "id".

        Raises:
            PyMongoError: Nếu insert thất bại (duplicate id, connection error...).
                          Để lỗi lan lên Service xử lý.
        """
        self.collection.insert_one(post_dict)
        logger.info(
            "[PostRepository.save] INSERT Post id='%s' — author='%s'.",
            post_dict.get("id"), post_dict.get("author_id"),
        )

    def toggle_like(self, post_id: str, user_id: str) -> bool:
        """
        Toggle like: thêm hoặc bỏ like của một user trên một bài viết.

        Logic atomic — KHÔNG cần đọc document trước, tránh race condition:
            Nếu user_id ĐÃ có trong mảng likes  → $pull  (bỏ like)
            Nếu user_id CHƯA có trong mảng likes → $addToSet (thêm like)

        Xác định trạng thái hiện tại bằng cách đếm matched_count sau mỗi lệnh:
            Thử $pull trước → nếu modified_count = 1: đã bỏ like thành công.
            Nếu $pull không sửa gì (modified_count = 0): thực hiện $addToSet.

        Args:
            post_id: ID của bài viết cần toggle like.
            user_id: ID của user thực hiện like/unlike.

        Returns:
            True  — Toggle thành công.
            False — Không tìm thấy Post hoặc lỗi MongoDB.
        """
        try:
            # ── Thử bỏ like trước ($pull) ─────────────────────────────
            pull_result = self.collection.update_one(
                {"id": post_id, "likes": user_id},   # filter: post tồn tại VÀ đã like
                {"$pull": {"likes": user_id}},
            )

            if pull_result.modified_count == 1:
                # user_id đã tồn tại trong likes → đã pull thành công = bỏ like
                logger.info(
                    "[PostRepository.toggle_like] BỎ LIKE — "
                    "post='%s', user='%s'.", post_id, user_id,
                )
                return True

            # ── Nếu chưa like → thêm like ($addToSet) ─────────────────
            # $addToSet tự đảm bảo không duplicate nếu race condition xảy ra
            push_result = self.collection.update_one(
                {"id": post_id},
                {"$addToSet": {"likes": user_id}},
            )

            if push_result.matched_count == 0:
                # Post không tồn tại
                logger.warning(
                    "[PostRepository.toggle_like] Không tìm thấy post='%s'.",
                    post_id,
                )
                return False

            logger.info(
                "[PostRepository.toggle_like] THÊM LIKE — "
                "post='%s', user='%s'.", post_id, user_id,
            )
            return True

        except PyMongoError as exc:
            logger.error(
                "[PostRepository.toggle_like] Lỗi MongoDB "
                "(post='%s', user='%s'): %s.", post_id, user_id, str(exc),
            )
            return False

    def add_comment(self, post_id: str, comment_dict: dict) -> bool:
        """
        Thêm một bình luận vào cuối mảng `comments` của Post.

        MongoDB atomic $push:
            db.posts.update_one(
                {"id": post_id},
                {"$push": {"comments": comment_dict}}
            )

        $push đảm bảo append an toàn ngay cả khi nhiều user comment đồng thời.

        Args:
            post_id     : ID của bài viết cần thêm bình luận.
            comment_dict: dict bình luận đầy đủ (có comment_id, created_at).

        Returns:
            True  — Thêm bình luận thành công.
            False — Không tìm thấy Post hoặc lỗi MongoDB.
        """
        try:
            result = self.collection.update_one(
                {"id": post_id},
                {"$push": {"comments": comment_dict}},
            )

            if result.matched_count == 0:
                logger.warning(
                    "[PostRepository.add_comment] Không tìm thấy post='%s'.",
                    post_id,
                )
                return False

            logger.info(
                "[PostRepository.add_comment] Thêm comment '%s' vào post='%s'.",
                comment_dict.get("comment_id"), post_id,
            )
            return True

        except PyMongoError as exc:
            logger.error(
                "[PostRepository.add_comment] Lỗi MongoDB (post='%s'): %s.",
                post_id, str(exc),
            )
            return False