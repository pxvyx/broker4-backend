"""
Module  : src/config/firebase_config.py
Layer   : Infrastructure / Configuration
Purpose : Khởi tạo Firebase Admin SDK — Singleton Pattern.

Cơ chế hoạt động:
    - init_firebase() chỉ khởi tạo app đúng 1 lần nhờ kiểm tra _apps.
    - Đọc đường dẫn file Service Account JSON từ biến môi trường
      FIREBASE_CREDENTIALS (cấu hình trong file .env).
    - Được gọi 1 lần duy nhất trong create_app() tại src/app.py.

Cấu hình .env cần có:
    FIREBASE_CREDENTIALS=/absolute/path/to/serviceAccountKey.json

Cách lấy file Service Account Key:
    Firebase Console → Project Settings → Service Accounts
    → Generate new private key → Tải file JSON về.
"""

import logging
import os

import firebase_admin
from firebase_admin import credentials
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)


def init_firebase() -> None:
    """
    Khởi tạo Firebase Admin SDK từ Service Account credentials.

    Kiểm tra `firebase_admin._apps` trước khi khởi tạo để đảm bảo
    Singleton — tránh lỗi "Firebase App named '[DEFAULT]' already exists"
    khi Flask reload trong debug mode.

    Raises:
        RuntimeError: Nếu biến môi trường FIREBASE_CREDENTIALS chưa cấu hình,
                      file không tồn tại, hoặc nội dung JSON không hợp lệ.
    """
    # ── Fast-path: đã khởi tạo rồi → bỏ qua ─────────────────────────
    if firebase_admin._apps:
        logger.debug("[Firebase] SDK đã được khởi tạo trước đó. Bỏ qua.")
        return

    # ── Đọc đường dẫn file credentials từ .env ────────────────────────
    credentials_path = os.getenv("FIREBASE_CREDENTIALS", "").strip()
    if not credentials_path:
        logger.critical(
            "[Firebase] Biến môi trường FIREBASE_CREDENTIALS chưa được cấu hình. "
            "Thêm đường dẫn tuyệt đối đến file serviceAccountKey.json vào .env."
        )
        raise RuntimeError(
            "FIREBASE_CREDENTIALS chưa được cấu hình trong .env."
        )

    if not os.path.isfile(credentials_path):
        logger.critical(
            "[Firebase] Không tìm thấy file credentials tại: '%s'. "
            "Kiểm tra lại đường dẫn trong FIREBASE_CREDENTIALS.",
            credentials_path,
        )
        raise RuntimeError(
            f"File Firebase credentials không tồn tại: '{credentials_path}'."
        )

    # ── Khởi tạo Firebase Admin SDK ───────────────────────────────────
    try:
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
        logger.info(
            "[Firebase] Khởi tạo Admin SDK thành công "
            "từ file: '%s'.", credentials_path,
        )

    except (ValueError, FirebaseError) as exc:
        logger.critical(
            "[Firebase] Khởi tạo thất bại — file credentials không hợp lệ "
            "hoặc thiếu quyền: %s", str(exc),
        )
        raise RuntimeError(
            f"Khởi tạo Firebase Admin SDK thất bại: {exc}"
        ) from exc