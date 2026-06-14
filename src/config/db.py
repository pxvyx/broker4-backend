"""
Module  : src/config/db.py
Layer   : Infrastructure / Configuration
Purpose : Quản lý kết nối MongoDB Atlas — cung cấp hàm get_db() dùng chung
          cho toàn bộ tầng Repositories.

Cơ chế hoạt động:
    - Dùng Singleton Pattern: MongoClient được khởi tạo đúng 1 lần duy nhất
      khi get_db() được gọi lần đầu, các lần sau tái sử dụng instance cũ.
    - pymongo.MongoClient tự quản lý Connection Pool bên trong — thread-safe.
    - URI đọc từ biến môi trường MONGO_URI (file .env).

Cấu hình .env cần có:
    MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority

Sử dụng trong Repository:
    from src.config.db import get_db
    collection = get_db()["projects"]
"""

import logging
import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConfigurationError, ConnectionFailure, ServerSelectionTimeoutError

# Nạp biến môi trường từ file .env (nếu có)
load_dotenv()

logger = logging.getLogger(__name__)

# ── Singleton state ────────────────────────────────────────────────────────────
_client: MongoClient | None = None
_db: Database | None = None

# ── Tên database cố định ───────────────────────────────────────────────────────
_DB_NAME = "broker4_db"


def get_db() -> Database:
    """
    Trả về đối tượng Database đã kết nối đến MongoDB Atlas.

    Lần đầu gọi: đọc MONGO_URI, khởi tạo MongoClient với Connection Pool,
                 ping server để xác nhận kết nối thành công.
    Các lần sau : tái sử dụng _client và _db đã có (Singleton).

    Connection Pool settings:
        maxPoolSize       = 50   — tối đa 50 kết nối đồng thời trong pool.
        minPoolSize       = 5    — giữ sẵn 5 kết nối để tái dùng ngay.
        connectTimeoutMS  = 5000 — timeout khi tạo kết nối mới: 5 giây.
        serverSelectionTimeoutMS = 5000 — timeout khi chọn server: 5 giây.

    Returns:
        pymongo.database.Database — đối tượng trỏ đến database 'broker4_db'.

    Raises:
        RuntimeError: Nếu MONGO_URI chưa được cấu hình hoặc kết nối thất bại.
    """
    global _client, _db

    # Nếu đã khởi tạo rồi → trả về ngay (Singleton fast-path)
    if _db is not None:
        return _db

    # ── Đọc URI từ biến môi trường ────────────────────────────────────
    mongo_uri = os.environ.get("MONGO_URI", "").strip()
    if not mongo_uri:
        logger.critical(
            "[DB] Biến môi trường MONGO_URI chưa được cấu hình. "
            "Thêm MONGO_URI vào file .env và khởi động lại ứng dụng."
        )
        raise RuntimeError(
            "MONGO_URI chưa được cấu hình. "
            "Kiểm tra file .env hoặc biến môi trường hệ thống."
        )

    # ── Khởi tạo MongoClient với Connection Pool ───────────────────────
    try:
        logger.info("[DB] Đang kết nối đến MongoDB Atlas...")

        _client = MongoClient(
            mongo_uri,
            maxPoolSize=50,
            minPoolSize=5,
            connectTimeoutMS=5_000,
            serverSelectionTimeoutMS=5_000,
        )

        # Ping để xác nhận kết nối thực sự thành công
        _client.admin.command("ping")
        logger.info("[DB] Kết nối MongoDB Atlas thành công → database='%s'.", _DB_NAME)

        _db = _client[_DB_NAME]
        return _db

    except ServerSelectionTimeoutError as exc:
        logger.critical(
            "[DB] Không thể kết nối MongoDB Atlas (timeout sau 5 giây). "
            "Kiểm tra lại MONGO_URI, IP Whitelist, và trạng thái cluster. "
            "Chi tiết: %s", str(exc),
        )
        raise RuntimeError(f"Kết nối MongoDB Atlas thất bại (timeout): {exc}") from exc

    except ConfigurationError as exc:
        logger.critical(
            "[DB] MONGO_URI không đúng định dạng. "
            "URI Atlas phải bắt đầu bằng 'mongodb+srv://...'. Chi tiết: %s", str(exc),
        )
        raise RuntimeError(f"MONGO_URI không hợp lệ: {exc}") from exc

    except ConnectionFailure as exc:
        logger.critical(
            "[DB] Lỗi kết nối MongoDB. Chi tiết: %s", str(exc),
        )
        raise RuntimeError(f"Kết nối MongoDB thất bại: {exc}") from exc
