# google_auth.py - ระบบการยืนยันตัวตน
from flask import redirect, session, url_for, request, jsonify
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# กำหนดค่าสำหรับ Google OAuth
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'openid'
]

# รับ URL จากสภาพแวดล้อม หรือใช้ localhost เป็นค่าตั้งต้น
REDIRECT_URI = os.environ.get('REDIRECT_URI')

# สร้าง Flow สำหรับ OAuth
def create_flow():
    """สร้าง OAuth Flow"""
    try:
        # พยายามใช้ตัวแปรสภาพแวดล้อมก่อน
        client_config = json.loads(os.environ.get('GOOGLE_CLIENT_SECRET', '{}'))
        if not client_config:
            raise ValueError("GOOGLE_CLIENT_SECRET is empty or invalid")
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        return flow
    except Exception as e:
        print(f"Error creating OAuth flow: {e}")
        raise ValueError("No valid OAuth credentials found.")

def get_valid_credentials():
    """
    ดึง credentials ที่ใช้งานได้ - ทำ auto-refresh ถ้าจำเป็น
    
    Returns:
        Credentials: credentials object ที่ใช้งานได้ หรือ None ถ้าไม่สำเร็จ
    """
    if 'credentials' not in session:
        return None
    
    try:
        # สร้าง Credentials object จาก session
        credentials = Credentials(**session['credentials'])
        
        # ตรวจสอบและ refresh อัตโนมัติ
        if credentials.expired and credentials.refresh_token:
            print("Token expired, refreshing...")
            credentials.refresh(Request())
            
            # อัปเดต session ด้วย credentials ใหม่
            _update_session_credentials(credentials)
            print("Token refreshed successfully")
        
        return credentials
        
    except RefreshError as e:
        print(f"Token refresh failed: {e}")
        # ลบ session และให้ login ใหม่
        session.clear()
        return None
    except Exception as e:
        print(f"Error getting valid credentials: {e}")
        return None

def _update_session_credentials(credentials):
    """อัปเดต credentials ใน session"""
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    session.permanent = True

def login_required(f):
    """
    Decorator สำหรับตรวจสอบการล็อกอิน
    จัดการ token refresh อัตโนมัติ
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        credentials = get_valid_credentials()
        if not credentials:
            # ถ้าเป็น AJAX request ให้ส่ง JSON response
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'error': 'การเข้าสู่ระบบหมดอายุ กรุณาเข้าสู่ระบบใหม่',
                    'auth_error': True,
                    'redirect_url': url_for('login_page')
                }), 401
            
            # ถ้าเป็น normal request ให้ redirect
            return redirect(url_for('login_page'))
        
        return f(*args, **kwargs)
    return decorated_function

def handle_auth_error(func):
    """
    Decorator สำหรับจัดการ auth errors ใน API calls
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RefreshError:
            session.clear()
            return jsonify({
                'error': 'การเข้าสู่ระบบหมดอายุ กรุณาเข้าสู่ระบบใหม่',
                'auth_error': True
            }), 401
        except Exception as e:
            error_msg = str(e).lower()
            if 'unauthorized' in error_msg or 'forbidden' in error_msg or 'credentials' in error_msg:
                session.clear()
                return jsonify({
                    'error': 'การเข้าสู่ระบบหมดอายุ กรุณาเข้าสู่ระบบใหม่',
                    'auth_error': True
                }), 401
            raise
    return wrapper