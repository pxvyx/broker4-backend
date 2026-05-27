"""
Module  : src/app.py
Purpose : Điểm khởi tạo Flask Application — App Factory Pattern.

Cách chạy ứng dụng:
    cd broker_4_0_backend/
    python -m flask --app src.app run --debug

Hoặc dùng lệnh:
    cd broker_4_0_backend/
    python src/app.py
"""

import logging
import os
from flask import Flask

# ── Import tất cả Blueprints ───────────────────────────────────────────────────
from src.controllers.project_controller  import project_bp
from src.controllers.matching_controller import matching_bp
from src.controllers.contract_controller import contract_bp
from src.controllers.review_controller   import review_bp



def create_app() -> Flask:
    """
    App Factory: khởi tạo và cấu hình Flask application.

    Sử dụng App Factory Pattern thay vì global app instance
    để dễ dàng tạo nhiều instance trong môi trường test.

    Returns:
        Flask application đã được cấu hình đầy đủ.
    """
    app = Flask(__name__)

    # ── Cấu hình Logging ──────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Đăng ký Blueprints ────────────────────────────────────────────
    # Mỗi Blueprint tương ứng với 1 nhóm tính năng trong luồng 7 bước.
    app.register_blueprint(project_bp)   # Bước 1 — POST /api/projects
    app.register_blueprint(matching_bp)  # Bước 2 — GET  /api/matches/<id>
    app.register_blueprint(contract_bp)  # Bước 3&4 — POST /api/contracts/...
    app.register_blueprint(review_bp)    # Bước 6 — POST /api/reviews


    from src.controllers.execution_controller import execution_bp
    from src.controllers.dashboard_controller import dashboard_bp

    app.register_blueprint(execution_bp)
    app.register_blueprint(dashboard_bp)

    # ── Log toàn bộ routes đã đăng ký ────────────────────────────────
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Broker 4.0 API — Routes đã đăng ký:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        methods = ", ".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        logger.info("  %-40s [%s]", rule.rule, methods)
    logger.info("=" * 60)

    return app


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True,
    )