"""
Module  : src/config/firebase_config.py
Layer   : Infrastructure / Configuration
Purpose : Khởi tạo Firebase Admin SDK — Singleton Pattern (Hỗ trợ đa môi trường).

Cơ chế hoạt động:
    - init_firebase() chỉ khởi tạo app đúng 1 lần nhờ kiểm tra _apps.
    - Chạy ở Local: Đọc đường dẫn file JSON từ biến FIREBASE_CREDENTIALS.
    - Chạy ở Vercel/Serverless: Đọc trực tiếp chuỗi JSON từ biến FIREBASE_CREDENTIALS.
    - Được gọi 1 lần duy nhất trong create_app() tại src/app.py.
"""

import json
import logging
import os

import firebase_admin
from firebase_admin import credentials
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)


def init_firebase() -> None:
    """
    Khởi tạo Firebase Admin SDK.
    Hỗ trợ cả đường dẫn file (Local) và chuỗi JSON (Production/Vercel).

    Raises:
        RuntimeError: Nếu biến môi trường FIREBASE_CREDENTIALS chưa cấu hình,
                      file không tồn tại, hoặc nội dung JSON không hợp lệ.
    """
    # ── Fast-path: đã khởi tạo rồi → bỏ qua ─────────────────────────
    if firebase_admin._apps:
        logger.debug("[Firebase] SDK đã được khởi tạo trước đó. Bỏ qua.")
        return

    # ── Đọc cấu hình từ .env hoặc Biến môi trường hệ thống ──────────
    cred_value = os.getenv("FIREBASE_CREDENTIALS", "").strip()
    
    if not cred_value:
        logger.critical(
            "[Firebase] Biến môi trường FIREBASE_CREDENTIALS chưa được cấu hình. "
            "Thêm đường dẫn file hoặc chuỗi JSON vào cấu hình hệ thống."
        )
        raise RuntimeError("FIREBASE_CREDENTIALS chưa được cấu hình.")

    # ── Phân luồng nạp cấu hình (File vs JSON String) ───────────────
    try:
        # Tình huống 1: Môi trường Local (Chứa đường dẫn file .json)
        if cred_value.endswith('.json'):
            if not os.path.isfile(cred_value):
                logger.critical(
                    "[Firebase] Không tìm thấy file credentials tại: '%s'.",
                    cred_value,
                )
                raise RuntimeError(f"File Firebase credentials không tồn tại: '{cred_value}'.")
            
            cred = credentials.Certificate(cred_value)
            source_info = f"file: '{cred_value}'"
            
        # Tình huống 2: Môi trường Vercel/Production (Chứa chuỗi JSON)
        else:
            try:
                cred_dict = json.loads(cred_value)
                cred = credentials.Certificate(cred_dict)
                source_info = "biến môi trường (JSON String)"
            except json.JSONDecodeError as e:
                logger.critical(
                    "[Firebase] Nội dung FIREBASE_CREDENTIALS không phải là file .json "
                    "và cũng không phải chuỗi JSON hợp lệ."
                )
                raise RuntimeError("Định dạng FIREBASE_CREDENTIALS không hợp lệ.") from e

        # ── Khởi tạo App ─────────────────────────────────────────────
        firebase_admin.initialize_app(cred)
        logger.info("[Firebase] Khởi tạo Admin SDK thành công từ %s.", source_info)

    except (ValueError, FirebaseError) as exc:
        logger.critical(
            "[Firebase] Khởi tạo thất bại — credentials không hợp lệ "
            "hoặc thiếu quyền: %s", str(exc),
        )
        raise RuntimeError(f"Khởi tạo Firebase Admin SDK thất bại: {exc}") from exc