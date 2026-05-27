from flask import Blueprint, request, jsonify
from src.services.execution_service import add_milestone, complete_milestone, get_project_milestones

execution_bp = Blueprint('execution', __name__, url_prefix='/api/execution')

def _ok(data, message="Thành công"):
    return jsonify({"success": True, "message": message, "data": data}), 200

def _err(message, status_code):
    return jsonify({"success": False, "message": message, "data": None}), status_code

@execution_bp.route('/projects/<project_id>/milestones', methods=['POST'])
def create_milestone(project_id):
    try:
        data = request.json or {}
        title = data.get('title')
        description = data.get('description', '')
        due_date = data.get('due_date')
        
        if not title or not due_date:
            return _err("Thiếu trường 'title' hoặc 'due_date'.", 400)
            
        milestone = add_milestone(project_id, title, description, due_date)
        return jsonify({"success": True, "message": "Thêm mốc tiến độ thành công", "data": milestone.to_dict()}), 201
    except LookupError as e:
        return _err(str(e), 404)
    except ValueError as e:
        return _err(str(e), 400)
    except Exception as e:
        return _err(str(e), 500)

@execution_bp.route('/milestones/<milestone_id>/complete', methods=['PATCH'])
def mark_milestone_completed(milestone_id):
    try:
        milestone = complete_milestone(milestone_id)
        return _ok(milestone.to_dict(), "Đã cập nhật mốc tiến độ thành Completed")
    except LookupError as e:
        return _err(str(e), 404)
    except Exception as e:
        return _err(str(e), 500)

@execution_bp.route('/projects/<project_id>/milestones', methods=['GET'])
def list_milestones(project_id):
    try:
        milestones = get_project_milestones(project_id)
        return _ok([ms.to_dict() for ms in milestones])
    except LookupError as e:
        return _err(str(e), 404)
    except Exception as e:
        return _err(str(e), 500)