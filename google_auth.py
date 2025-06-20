# google_auth.py - ระบบการยืนยันตัวตน
from flask import redirect, session, url_for, request, jsonify
import os
import pathlib
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from functools import wraps
from dotenv import load_dotenv
import json
import time

load_dotenv()  # โหลดตัวแปรจากไฟล์ .env

print(f"REDIRECT_URI loaded: {os.environ.get('REDIRECT_URI')}")  # เพิ่มเพื่อตรวจสอบ

# กำหนดค่าสำหรับ Google OAuth
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'openid'  # เพิ่ม scope นี้
]

# รับ URL จากสภาพแวดล้อม หรือใช้ localhost เป็นค่าตั้งต้น
REDIRECT_URI = os.environ.get('REDIRECT_URI')

# สร้าง Flow สำหรับ OAuth
def create_flow():
    try:
        # พยายามใช้ตัวแปรสภาพแวดล้อมก่อน
        print("Trying to use GOOGLE_CLIENT_SECRET from environment")
        client_config = json.loads(os.environ.get('GOOGLE_CLIENT_SECRET', '{}'))
        if not client_config:
            raise ValueError("GOOGLE_CLIENT_SECRET is empty or invalid")
        
        redirect_uri = os.environ.get('REDIRECT_URI')
        print(f"Using redirect_uri: {redirect_uri}")
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        return flow
    except Exception as e:
        print(f"Error using GOOGLE_CLIENT_SECRET: {e}")
        raise ValueError("No valid OAuth credentials found. Please set GOOGLE_CLIENT_SECRET environment variable.")

def refresh_credentials():
    """
    ฟังก์ชันสำหรับต่ออายุ credentials
    
    Returns:
        bool: True ถ้าต่ออายุสำเร็จ, False ถ้าไม่สำเร็จ
    """
    if 'credentials' not in session:
        print("No credentials in session")
        return False
    
    try:
        # สร้าง Credentials object จาก session
        credentials = Credentials(**session['credentials'])
        
        # ตรวจสอบว่า credentials หมดอายุหรือไม่
        if not credentials.expired:
            print("Credentials are still valid")
            return True
        
        print("Credentials expired, attempting to refresh...")
        
        # ตรวจสอบว่ามี refresh_token หรือไม่
        if not credentials.refresh_token:
            print("No refresh token available")
            return False
        
        # Import ที่จำเป็นสำหรับการ refresh
        from google.auth.transport.requests import Request
        
        # ต่ออายุ credentials
        credentials.refresh(Request())
        
        # อัปเดต session ด้วย credentials ใหม่
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # เพิ่มเวลาที่ refresh
        session['credentials_refreshed_at'] = time.time()
        
        print("Credentials refreshed successfully")
        return True
        
    except Exception as e:
        print(f"Error refreshing credentials: {e}")
        return False

def get_valid_credentials():
    """
    ดึง credentials ที่ยังใช้งานได้ (refresh อัตโนมัติถ้าจำเป็น)
    
    Returns:
        Credentials: credentials object ที่ใช้งานได้ หรือ None ถ้าไม่สำเร็จ
    """
    if 'credentials' not in session:
        return None
    
    try:
        credentials = Credentials(**session['credentials'])
        
        # ถ้า credentials หมดอายุ ให้ลองต่ออายุ
        if credentials.expired and credentials.refresh_token:
            if refresh_credentials():
                # ดึง credentials ใหม่หลังจาก refresh
                credentials = Credentials(**session['credentials'])
            else:
                return None
        
        return credentials
        
    except Exception as e:
        print(f"Error getting valid credentials: {e}")
        return None

# เช็คว่ามีการล็อกอินหรือไม่ - ใช้เป็น decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return redirect(url_for('login_page'))
        
        # ตรวจสอบและต่ออายุ credentials ถ้าจำเป็น
        credentials = get_valid_credentials()
        if not credentials:
            # ถ้าไม่สามารถต่ออายุได้ ให้ล้าง session และ redirect ไป login
            session.clear()
            return redirect(url_for('login_page'))
        
        return f(*args, **kwargs)
    return decorated_function

# เพิ่ม API endpoint สำหรับ refresh token จาก frontend
def create_refresh_endpoint(app):
    """
    สร้าง endpoint สำหรับ refresh credentials จาก frontend
    """
    @app.route('/api/refresh-token', methods=['POST'])
    @login_required
    def refresh_token_endpoint():
        try:
            success = refresh_credentials()
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Token refreshed successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to refresh token',
                    'redirect': url_for('login_page')
                }), 401
        except Exception as e:
            print(f"Error in refresh token endpoint: {e}")
            return jsonify({
                'success': False,
                'message': 'Error refreshing token',
                'redirect': url_for('login_page')
            }), 500