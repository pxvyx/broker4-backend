"""
Module  : src/services/contract_service.py
Layer   : Services (Business Logic)
Purpose : Xử lý nghiệp vụ Hợp đồng — Đàm phán và Ký kết.

Luồng 7 bước — phụ trách:
    Bước 3 — Đàm phán   : initiate_negotiation() → Contract(status="Draft")
                           + Project(status="Negotiating")
    Bước 4 — Ký hợp đồng: sign_contract()        → Contract(status="Active")
                           + Project(status="In Progress")

Biểu đồ chuyển trạng thái:
    Project : Pending ──[initiate]──► Negotiating ──[sign]──► In Progress
    Contract:           Draft     ──────────────[sign]──────► Active
"""

import logging
import uuid
from datetime import date

from src.models.contract import Contract, CONTRACT_TYPES
from src.models.project import Project
from src.repositories.contract_repo import ContractRepository
from src.repositories.project_repo import ProjectRepository
from src.repositories.expert_repo import ExpertRepository

logger = logging.getLogger(__name__)

_contract_repo = ContractRepository()
_project_repo = ProjectRepository()
_expert_repo = ExpertRepository()


def initiate_negotiation(project_id: str, expert_id: str) -> Contract:
    """
    Bước 3 — Khởi tạo đàm phán: tạo Contract(type=MOU, status=Draft)
    và chuyển Project sang status=Negotiating.

    Điều kiện tiên quyết:
        - Project phải tồn tại và đang ở status Pending.
        - Expert phải tồn tại và đang available.

    Args:
        project_id: ID của Project cần đàm phán.
        expert_id : ID của Expert được chọn để đàm phán.

    Returns:
        Contract object vừa được tạo (status="Draft").

    Raises:
        LookupError: Nếu Project hoặc Expert không tồn tại.
        ValueError : Nếu Project không ở trạng thái hợp lệ,
                     hoặc Expert không available.
        IOError    : Nếu ghi dữ liệu thất bại.
    """
    # ── Validate Project ───────────────────────────────────────────────
    project = _project_repo.get_by_id(project_id)
    if not project:
        raise LookupError(f"Không tìm thấy Project với id='{project_id}'.")
    if project.status != "Pending":
        raise ValueError(
            f"Project id='{project_id}' đang ở status='{project.status}'. "
            "Chỉ có thể bắt đầu đàm phán khi Project ở trạng thái Pending."
        )

    # ── Validate Expert ────────────────────────────────────────────────
    expert = _expert_repo.get_by_id(expert_id)
    if not expert:
        raise LookupError(f"Không tìm thấy Expert với id='{expert_id}'.")
    if not expert.is_available:
        raise ValueError(
            f"Expert id='{expert_id}' ({expert.expert_name}) "
            "hiện không available để nhận dự án mới."
        )

    # ── Tạo Contract mới (MOU Draft) ──────────────────────────────────
    contract = Contract(
        id=f"CTR-{uuid.uuid4().hex[:8].upper()}",
        project_id=project_id,
        expert_id=expert_id,
        contract_type="MOU",    # Giai đoạn đàm phán bắt đầu bằng MOU
        status="Draft",
        notes=(
            f"MOU khởi tạo tự động ngày {date.today().isoformat()}. "
            "Các điều khoản cần được hai bên thống nhất trước khi ký."
        ),
    )

    # ── Chuyển Project → Negotiating ──────────────────────────────────
    project.status = "Negotiating"

    # ── Lưu cả hai (2 thao tác riêng biệt — giới hạn của JSON mock) ───
    if not _contract_repo.save(contract):
        raise IOError("Lỗi hệ thống: Không thể lưu Contract vào database.")
    if not _project_repo.save(project):
        raise IOError("Lỗi hệ thống: Không thể cập nhật trạng thái Project.")

    logger.info(
        "[ContractService] initiate_negotiation — Contract='%s' (Draft), "
        "Project='%s' → Negotiating.",
        contract.id, project_id,
    )
    return contract


def sign_contract(contract_id: str) -> Contract:
    """
    Bước 4 — Ký kết hợp đồng: chuyển Contract → Active
    và Project → In Progress.

    Điều kiện tiên quyết:
        - Contract phải tồn tại và đang ở status Draft.

    Args:
        contract_id: ID của Contract cần ký kết.

    Returns:
        Contract object đã cập nhật (status="Active").

    Raises:
        LookupError: Nếu Contract không tồn tại.
        ValueError : Nếu Contract không ở trạng thái Draft.
        IOError    : Nếu ghi dữ liệu thất bại.
    """
    # ── Validate Contract ──────────────────────────────────────────────
    contract = _contract_repo.get_by_id(contract_id)
    if not contract:
        raise LookupError(f"Không tìm thấy Contract với id='{contract_id}'.")
    if contract.status != "Draft":
        raise ValueError(
            f"Contract id='{contract_id}' đang ở status='{contract.status}'. "
            "Chỉ có thể ký kết khi Contract ở trạng thái Draft."
        )

    # ── Cập nhật Contract → Active ────────────────────────────────────
    today = date.today().isoformat()
    contract.status = "Active"
    contract.signed_date = today
    contract.start_date = today

    # ── Cập nhật Project liên quan → In Progress ──────────────────────
    project = _project_repo.get_by_id(contract.project_id)
    if project:
        project.status = "In Progress"
        _project_repo.save(project)
        logger.info(
            "[ContractService] Project id='%s' → In Progress.", project.id
        )
    else:
        # Project không tìm thấy — log warning nhưng vẫn tiến hành ký HĐ
        logger.warning(
            "[ContractService] sign_contract: Không tìm thấy Project id='%s' "
            "để cập nhật status. Contract vẫn được ký.",
            contract.project_id,
        )

    # ── Lưu Contract đã cập nhật ──────────────────────────────────────
    if not _contract_repo.save(contract):
        raise IOError("Lỗi hệ thống: Không thể lưu Contract sau khi ký.")

    logger.info(
        "[ContractService] sign_contract — Contract='%s' → Active, "
        "signed_date='%s'.",
        contract_id, today,
    )
    return contract