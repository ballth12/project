# server.py
from waitress import serve
from app import app
import os

# กำหนดพอร์ตที่ต้องการใช้ (ต้องตรงกับการตั้งค่า Port Forwarding)
port = int(os.environ.get("PORT", 8080))

if __name__ == '__main__':
    print(f"Starting Room Meter App on port {port}...")
    # ให้ Waitress รับการเชื่อมต่อจากทุก interface
    serve(app, host='0.0.0.0', port=port)
    print("Server started. Press Ctrl+C to stop.")