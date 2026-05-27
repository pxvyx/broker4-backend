import uuid
from typing import List
from src.models.milestone import Milestone
from src.repositories.project_repo import ProjectRepository
from src.repositories.milestone_repo import MilestoneRepository

_project_repo = ProjectRepository()
_milestone_repo = MilestoneRepository()

def add_milestone(project_id: str, title: str, description: str, due_date: str) -> Milestone:
    project = _project_repo.get_by_id(project_id)
    if not project:
        raise LookupError(f"Không tìm thấy Project với ID: {project_id}")
        
    if project.status != "In Progress":
        raise ValueError("Chỉ được thêm mốc tiến độ (Milestone) khi dự án đang ở trạng thái 'In Progress'.")
        
    new_id = f"MLS-{uuid.uuid4().hex[:8].upper()}"
    milestone = Milestone(
        id=new_id,
        project_id=project_id,
        title=title,
        description=description,
        due_date=due_date,
        status="Pending"
    )
    
    success = _milestone_repo.save(milestone)
    if not success:
        raise IOError("Lỗi hệ thống: Không thể lưu Milestone vào file.")
        
    return milestone

def complete_milestone(milestone_id: str) -> Milestone:
    milestone = _milestone_repo.get_by_id(milestone_id)
    if not milestone:
        raise LookupError(f"Không tìm thấy Milestone với ID: {milestone_id}")
        
    milestone.status = "Completed"
    success = _milestone_repo.save(milestone)
    if not success:
        raise IOError("Lỗi hệ thống: Không thể cập nhật trạng thái Milestone.")
        
    return milestone

def get_project_milestones(project_id: str) -> List[Milestone]:
    # Validate project exists
    if not _project_repo.get_by_id(project_id):
        raise LookupError(f"Không tìm thấy Project với ID: {project_id}")
    return _milestone_repo.get_by_project_id(project_id)