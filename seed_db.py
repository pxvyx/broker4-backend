"""
Script mồi dữ liệu (Seed) từ file JSON lên MongoDB Atlas.
Chạy bằng lệnh: python seed_db.py
"""
import json
import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

# Bật log để xem tiến trình
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Tải biến môi trường từ file .env
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    logging.error("❌ Không tìm thấy MONGO_URI trong file .env")
    exit(1)

def seed_data():
    try:
        # 1. Kết nối lên MongoDB Atlas
        logging.info("Đang kết nối tới MongoDB Atlas...")
        client = MongoClient(MONGO_URI)
        db = client["broker4_db"] # Tên Database của bạn
        
        # 2. Định nghĩa các file JSON và Collection tương ứng
        collections_to_seed = {
            "experts": "data/experts.json",
            "projects": "data/projects.json",
            # Nếu bạn có smes.json hay reviews.json, cứ thêm vào đây
        }
        
        # 3. Đọc file JSON và đẩy lên
        for collection_name, file_path in collections_to_seed.items():
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                if data: # Nếu file có dữ liệu
                    collection = db[collection_name]
                    
                    # Xóa dữ liệu cũ (nếu có) để tránh bị trùng lặp khi chạy lại script
                    collection.delete_many({}) 
                    
                    # Đẩy toàn bộ mảng JSON lên MongoDB trong 1 nốt nhạc
                    collection.insert_many(data)
                    logging.info(f"✅ Đã đẩy {len(data)} bản ghi lên collection '{collection_name}' thành công!")
            else:
                logging.warning(f"⚠️ Không tìm thấy file {file_path}")

        logging.info("🎉 HOÀN TẤT SEED DỮ LIỆU!")
        
    except Exception as e:
        logging.error(f"❌ Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    seed_data()