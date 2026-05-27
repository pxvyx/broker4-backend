from typing import Dict, Any
from src.repositories.project_repo import ProjectRepository
from src.repositories.expert_repo import ExpertRepository
from src.repositories.contract_repo import ContractRepository

_project_repo = ProjectRepository()
_expert_repo = ExpertRepository()
_contract_repo = ContractRepository()

def get_platform_stats() -> Dict[str, Any]:
    projects = _project_repo.get_all()
    experts = _expert_repo.get_all()
    contracts = _contract_repo.get_all()
    
    # 1. Thống kê số lượng dự án theo trạng thái
    status_counts = {"Pending": 0, "Negotiating": 0, "In Progress": 0, "Completed": 0}
    for p in projects:
        if getattr(p, 'status', '') in status_counts:
            status_counts[p.status] += 1
            
    # 2. Lấy Top 3 Chuyên gia có rating cao nhất
    # Dùng (getattr() or 0) để đề phòng trường hợp rating bị null/None
    sorted_experts = sorted(experts, key=lambda e: (getattr(e, 'rating', 0) or 0), reverse=True)
    top_3_experts = [e.to_dict() for e in sorted_experts[:3]]
    
    # 3. Tính tổng giá trị hợp đồng (Active và Closed)
    # Dùng (getattr() or 0) để ép kiểu các hợp đồng chưa nhập giá (giá trị None) thành 0
    total_value = sum(
        (getattr(c, 'value', 0) or 0) for c in contracts 
        if getattr(c, 'status', '') in ["Active", "Closed"]
    )
    
    return {
        "total_projects": len(projects),
        "projects_by_status": status_counts,
        "top_experts": top_3_experts,
        "total_contract_value": total_value
    }