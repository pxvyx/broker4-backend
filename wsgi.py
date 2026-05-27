# File: wsgi.py
from src.app import create_app

# Khởi tạo ứng dụng Flask để Gunicorn có thể gọi
app = create_app()

if __name__ == "__main__":
    app.run()