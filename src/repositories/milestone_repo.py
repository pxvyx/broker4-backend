from typing import List, Optional
from src.repositories.json_repository import JsonRepository
from src.models.milestone import Milestone

class MilestoneRepository(JsonRepository):
    def __init__(self):
        # Truyền trực tiếp tên file vào constructor của lớp cha
        super().__init__("milestones.json")

    def get_all(self) -> List[Milestone]:
        # read_json() không cần nhận tham số file_name nữa
        data = self.read_json()
        return [Milestone.from_dict(item) for item in data]

    def get_by_id(self, milestone_id: str) -> Optional[Milestone]:
        for ms in self.get_all():
            if ms.id == milestone_id:
                return ms
        return None

    def get_by_project_id(self, project_id: str) -> List[Milestone]:
        return [ms for ms in self.get_all() if ms.project_id == project_id]

    def save(self, milestone: Milestone) -> bool:
        all_ms = self.get_all()
        updated = False
        
        # Upsert logic
        for i, ms in enumerate(all_ms):
            if ms.id == milestone.id:
                all_ms[i] = milestone
                updated = True
                break
                
        if not updated:
            all_ms.append(milestone)
            
        # write_json() chỉ cần truyền data vào, không cần truyền file_name
        return self.write_json([ms.to_dict() for ms in all_ms])