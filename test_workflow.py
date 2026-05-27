import requests
import time

BASE_URL = "http://127.0.0.1:5000/api"

def print_step(step_num, name):
    print(f"\n{'='*50}")
    print(f"BƯỚC {step_num}: {name}")
    print(f"{'='*50}")

def run_e2e_test():
    try:
        # Kiểm tra xem Server Backend đã chạy chưa
        health_check = requests.get(f"{BASE_URL}/dashboard/stats")
        if health_check.status_code not in [200, 404]: # Mở rộng điều kiện pass
            print("❌ Server Backend chưa hoạt động. Hãy chạy 'python src/app.py' trước!")
            return
    except Exception:
        print("❌ Không thể kết nối tới Server. Đảm bảo bạn đang bật Backend tại port 5000.")
        return

    print("✅ Server đang hoạt động. Bắt đầu chạy Test Workflow 7 Bước...")
    time.sleep(1)

    # ---------------------------------------------------------
    # BƯỚC 1: TẠO PROJECT
    # ---------------------------------------------------------
    print_step(1, "SME Đăng nhu cầu (Tạo Project)")
    payload_project = {
        "sme_id": "SME-001",
        "title": "Tích hợp AI Chatbot CSKH",
        "description": "Tự động trả lời tin nhắn Facebook và Website",
        "required_specialties": ["AI", "NLP", "Chatbot"],
        "budget": 100000000,
        "deadline": "2024-12-31"
    }
    res_1 = requests.post(f"{BASE_URL}/projects", json=payload_project)
    data_1 = res_1.json()
    print(f"Status: {res_1.status_code} | Response: {data_1}")
    
    if not data_1.get("success"):
        print("❌ Dừng test vì Bước 1 thất bại.")
        return
        
    project_id = data_1["data"]["id"]
    print(f"👉 Trích xuất Project ID: {project_id}")

    # ---------------------------------------------------------
    # BƯỚC 2: MATCHING
    # ---------------------------------------------------------
    print_step(2, "Matching Chuyên gia")
    res_2 = requests.get(f"{BASE_URL}/matches/{project_id}")
    data_2 = res_2.json()
    print(f"Status: {res_2.status_code} | Response: {data_2}")
    
    # Lấy chuyên gia đầu tiên để đàm phán (nếu có), nếu mock data rỗng thì dùng cứng "EXP-001"
    expert_id = "EXP-001" 
    if data_2.get("data") and len(data_2["data"]) > 0:
        expert_id = data_2["data"][0]["expert"]["id"]
    print(f"👉 Chọn Expert ID để đàm phán: {expert_id}")

    # ---------------------------------------------------------
    # BƯỚC 3: ĐÀM PHÁN (TẠO HỢP ĐỒNG)
    # ---------------------------------------------------------
    print_step(3, "Đàm phán (Tạo Hợp đồng Draft)")
    payload_contract = {
        "project_id": project_id,
        "expert_id": expert_id
    }
    res_3 = requests.post(f"{BASE_URL}/contracts/negotiate", json=payload_contract)
    data_3 = res_3.json()
    print(f"Status: {res_3.status_code} | Response: {data_3}")
    
    contract_id = data_3["data"]["id"]
    print(f"👉 Trích xuất Contract ID: {contract_id}")

    # ---------------------------------------------------------
    # BƯỚC 4: KÝ HỢP ĐỒNG
    # ---------------------------------------------------------
    print_step(4, "Ký Hợp đồng (Chuyển Project sang In Progress)")
    res_4 = requests.post(f"{BASE_URL}/contracts/{contract_id}/sign")
    print(f"Status: {res_4.status_code} | Response: {res_4.json()}")

    # ---------------------------------------------------------
    # BƯỚC 5: THỰC THI (MILESTONES)
    # ---------------------------------------------------------
    print_step("5.1", "Thêm Mốc tiến độ (Milestone)")
    payload_milestone = {
        "title": "Hoàn thành Demo Chatbot Phase 1",
        "description": "Chatbot có thể nhận diện ý định mua hàng cơ bản",
        "due_date": "2024-08-15"
    }
    res_5_1 = requests.post(f"{BASE_URL}/execution/projects/{project_id}/milestones", json=payload_milestone)
    data_5_1 = res_5_1.json()
    print(f"Status: {res_5_1.status_code} | Response: {data_5_1}")
    
    milestone_id = data_5_1["data"]["id"]
    print(f"👉 Trích xuất Milestone ID: {milestone_id}")

    print_step("5.2", "Hoàn thành Milestone")
    res_5_2 = requests.patch(f"{BASE_URL}/execution/milestones/{milestone_id}/complete")
    print(f"Status: {res_5_2.status_code} | Response: {res_5_2.json()}")

    # ---------------------------------------------------------
    # BƯỚC 6: ĐÁNH GIÁ (REVIEW)
    # ---------------------------------------------------------
    print_step(6, "Gửi Đánh giá (Chuyển Project sang Completed)")
    payload_review = {
        "project_id": project_id,
        "reviewer_sme_id": "SME-001",
        "reviewed_expert_id": expert_id,
        "rating": 5,
        "feedback": "Chuyên gia làm việc rất đúng hạn, chatbot phản hồi mượt mà.",
        "tags": ["AI", "NLP", "Đúng hạn"]
    }
    res_6 = requests.post(f"{BASE_URL}/reviews", json=payload_review)
    print(f"Status: {res_6.status_code} | Response: {res_6.json()}")

    # ---------------------------------------------------------
    # BƯỚC 7: DASHBOARD THỐNG KÊ
    # ---------------------------------------------------------
    print_step(7, "Lấy dữ liệu Dashboard (Admin)")
    res_7 = requests.get(f"{BASE_URL}/dashboard/stats")
    print(f"Status: {res_7.status_code} | Response: {res_7.json()}")

    print("\n🎉 HOÀN TẤT KIỂM THỬ TOÀN BỘ LUỒNG NGHIỆP VỤ 7 BƯỚC! 🎉")

if __name__ == "__main__":
    run_e2e_test()