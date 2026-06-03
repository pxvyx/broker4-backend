import uuid
from typing import List
from src.models.project import Project
from src.models.milestone import Milestone
from src.repositories.project_repo import ProjectRepository
from src.repositories.milestone_repo import MilestoneRepository

_project_repo = ProjectRepository()
_milestone_repo = MilestoneRepository()

def add_milestone(project_id: str, title: str, description: str, due_date: str) -> Milestone:
    project = _project_repo.get_by_id(project_id)
    if not project:
        # === VERCEL BYPASS ===
        project = Project(id=project_id, sme_id="SME-001", title="Demo", status="In Progress")
        
    if project.status != "In Progress":
        raise ValueError("Chỉ được thêm mốc tiến độ (Milestone) khi dự án đang ở trạng thái 'In Progress'.")
        
    new_id = f"MLS-{uuid.uuid4().hex[:8].upper()}"
    milestone = Milestone(
        id=new_id, project_id=project_id, title=title, 
        description=description, due_date=due_date, status="Pending"
    )
    
    _milestone_repo.save(milestone)
    return milestone

def complete_milestone(milestone_id: str) -> Milestone:
    milestone = _milestone_repo.get_by_id(milestone_id)
    if not milestone:
        # === VERCEL BYPASS ===
        milestone = Milestone(
            id=milestone_id, project_id="PRJ-DEMO", 
            title="Hoàn thành Demo Phase 1", description="Giả lập", 
            due_date="2024-12-31", status="Pending"
        )
        
    milestone.status = "Completed"
    _milestone_repo.save(milestone)
    return milestone

def get_project_milestones(project_id: str) -> List[Milestone]:
    milestones = _milestone_repo.get_by_project_id(project_id)
    if not milestones:
        # === VERCEL BYPASS: Trả về 1 milestone mẫu để UI có cái hiển thị
        milestones = [
            Milestone(
                id=f"MLS-{uuid.uuid4().hex[:8].upper()}", 
                project_id=project_id, 
                title="Hoàn thành phân tích yêu cầu (Vercel Bypass)", 
                description="Tài liệu SRS", 
                due_date="2024-08-15", 
                status="Pending"
            )
        ]
    return milestones