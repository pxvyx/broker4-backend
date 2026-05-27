"""
Module  : src/controllers/contract_controller.py
Layer   : Controllers (Routing & HTTP Response)
Purpose : Định nghĩa API endpoints cho Hợp đồng.

Endpoints:
    POST /api/contracts/negotiate       — Khởi tạo đàm phán (Bước 3)
    POST /api/contracts/<id>/sign       — Ký kết hợp đồng   (Bước 4)
"""

import logging
from flask import Blueprint, request, jsonify

from src.services.contract_service import initiate_negotiation, sign_contract

logger = logging.getLogger(__name__)

contract_bp = Blueprint("contract", __name__, url_prefix="/api/contracts")


def _ok(data, message: str = "", status_code: int = 200):
    return jsonify({"success": True, "message": message, "data": data}), status_code


def _err(message: str, status_code: int = 400):
    return jsonify({"success": False, "message": message, "data": None}), status_code


@contract_bp.route("/negotiate", methods=["POST"])
def negotiate_endpoint():
    """
    POST /api/contracts/negotiate
    Khởi tạo đàm phán giữa SME và Expert — Bước 3.
    Tạo Contract(type=MOU, status=Draft) và chuyển Project → Negotiating.

    Request body (JSON):
    {
        "project_id" : "PRJ-XXXXXXXX",  (bắt buộc)
        "expert_id"  : "EXP-001"        (bắt buộc)
    }

    Response 201: Contract Draft vừa tạo.
    Response 400: Thiếu input hoặc trạng thái không hợp lệ.
    Response 404: Không tìm thấy Project hoặc Expert.
    Response 500: Lỗi hệ thống.
    """
    body = request.get_json(silent=True) or {}
    project_id = body.get("project_id", "").strip()
    expert_id = body.get("expert_id", "").strip()

    if not project_id or not expert_id:
        return _err("project_id và expert_id là bắt buộc.", 400)

    try:
        contract = initiate_negotiation(project_id, expert_id)
        return _ok(
            data=contract.to_dict(),
            message=(
                f"Đã khởi tạo đàm phán. Contract '{contract.id}' "
                f"(MOU - Draft) đã được tạo."
            ),
            status_code=201,
        )

    except LookupError as exc:
        logger.warning("[ContractController.negotiate] LookupError: %s", str(exc))
        return _err(str(exc), 404)

    except ValueError as exc:
        logger.warning("[ContractController.negotiate] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except IOError as exc:
        logger.error("[ContractController.negotiate] IOError: %s", str(exc))
        return _err(str(exc), 500)


@contract_bp.route("/<contract_id>/sign", methods=["POST"])
def sign_contract_endpoint(contract_id: str):
    """
    POST /api/contracts/<contract_id>/sign
    Ký kết hợp đồng chính thức — Bước 4.
    Chuyển Contract → Active và Project → In Progress.

    Response 200: Contract đã Active.
    Response 400: Contract không ở trạng thái Draft.
    Response 404: Không tìm thấy Contract.
    Response 500: Lỗi hệ thống.
    """
    try:
        contract = sign_contract(contract_id)
        return _ok(
            data=contract.to_dict(),
            message=(
                f"Hợp đồng '{contract.id}' đã được ký kết thành công. "
                f"Dự án bắt đầu từ {contract.signed_date}."
            ),
        )

    except LookupError as exc:
        logger.warning("[ContractController.sign] LookupError: %s", str(exc))
        return _err(str(exc), 404)

    except ValueError as exc:
        logger.warning("[ContractController.sign] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except IOError as exc:
        logger.error("[ContractController.sign] IOError: %s", str(exc))
        return _err(str(exc), 500)