from flask import Blueprint, jsonify
from src.services.dashboard_service import get_platform_stats

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@dashboard_bp.route('/stats', methods=['GET'])
def get_stats():
    try:
        stats = get_platform_stats()
        return jsonify({"success": True, "message": "Lấy thống kê thành công", "data": stats}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500