from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Milestone:
    id: str
    project_id: str
    title: str
    description: str
    due_date: str
    status: str = "Pending"  # Pending | Completed

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Milestone":
        return cls(
            id=data.get("id", ""),
            project_id=data.get("project_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            due_date=data.get("due_date", ""),
            status=data.get("status", "Pending")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date,
            "status": self.status
        }