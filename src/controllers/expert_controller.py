from flask import Blueprint, jsonify
from src.services import expert_service

expert_bp = Blueprint('expert_bp', __name__)

@expert_bp.route('/experts', methods=['GET'])
def get_experts():
    try:
        experts = expert_service.get_all_experts()
        
        # Chuyển đổi list object sang dạng dict để jsonify có thể serialize
        # (Nếu repository đã trả về dict thì không cần .to_dict())
        experts_data = [
            expert.to_dict() if hasattr(expert, 'to_dict') else expert 
            for expert in experts
        ]
        
        return jsonify({
            "success": True,
            "message": "Lấy danh bạ chuyên gia thành công.",
            "data": experts_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Lỗi hệ thống: {str(e)}",
            "data": None
        }), 500