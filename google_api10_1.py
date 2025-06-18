# auth.py - ระบบการยืนยันตัวตน
from flask import redirect, session, url_for, request, jsonify
import os
import pathlib
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from functools import wraps
from dotenv import load_dotenv
import json
import time
from googleapiclient.errors import HttpError

load_dotenv(override=True)  # โหลดตัวแปรจากไฟล์ .env

print(f"REDIRECT_URI loaded: {os.environ.get('REDIRECT_URI')}")  # เพิ่มเพื่อตรวจสอบ

# กำหนดค่าสำหรับ Google OAuth
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'openid'  # เพิ่ม scope นี้
]

# ต้องสร้างไฟล์ client_secret.json ที่ได้จาก Google Cloud Console
CLIENT_SECRET_FILE = 'client_secret.json'
# รับ URL จากสภาพแวดล้อม หรือใช้ localhost เป็นค่าตั้งต้น
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'https://room-meter.online/callback')

# สร้าง Flow สำหรับ OAuth
def create_flow():
    try:
        # พยายามใช้ตัวแปรสภาพแวดล้อมก่อน
        print("Trying to use GOOGLE_CLIENT_SECRET from environment")
        client_config = json.loads(os.environ.get('GOOGLE_CLIENT_SECRET', '{}'))
        if not client_config:
            raise ValueError("GOOGLE_CLIENT_SECRET is empty or invalid")
        
        redirect_uri = os.environ.get('REDIRECT_URI', 'https://room-meter.online/callback')
        print(f"Using redirect_uri: {redirect_uri}")
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        return flow
    except Exception as e:
        print(f"Error using GOOGLE_CLIENT_SECRET: {e}")
        
        # ถ้าไม่สำเร็จ ให้ลองใช้ไฟล์
        if os.path.exists(CLIENT_SECRET_FILE):
            print(f"Falling back to {CLIENT_SECRET_FILE}")
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                scopes=SCOPES,
                redirect_uri=os.environ.get('REDIRECT_URI', 'https://room-meter.online/callback')
            )
            return flow
        else:
            raise ValueError("No valid OAuth credentials found")

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

# เช็คว่ามีการล็อกอินหรือไม่ - ใช้เป็น decorator (ปรับปรุงแล้ว)
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

# สร้าง Drive service จาก credentials (ปรับปรุงแล้ว)
def get_drive_service():
    credentials = get_valid_credentials()
    if not credentials:
        return None
    
    try:
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        print(f"Error creating Drive service: {e}")
        return None

# สร้าง Sheets service จาก credentials (ปรับปรุงแล้ว)
def get_sheets_service():
    credentials = get_valid_credentials()
    if not credentials:
        return None
    
    try:
        return build('sheets', 'v4', credentials=credentials)
    except Exception as e:
        print(f"Error creating Sheets service: {e}")
        return None

# สร้างโฟลเดอร์และ Sheets สำหรับผู้ใช้ (ปรับปรุง error handling)
def create_user_resources(user_email):
    """
    สร้างโฟลเดอร์และ Sheets สำหรับผู้ใช้
    
    Args:
        user_email (str): อีเมลของผู้ใช้
        
    Returns:
        tuple: (folder_id, sheet_id)
    """
    drive_service = get_drive_service()
    sheets_service = get_sheets_service()
    
    if not drive_service or not sheets_service:
        print("Error: Drive or Sheets service is not initialized")
        return None, None
    
    # ตรวจสอบว่ามีโฟลเดอร์ "RoomMeterApp" หรือไม่
    try:
        print(f"Searching for RoomMeterApp folder for user {user_email}")
        results = drive_service.files().list(
            q="name='RoomMeterApp' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folder_id = None
        items = results.get('files', [])
        
        if not items:
            print("Creating new RoomMeterApp folder")
            # สร้างโฟลเดอร์ใหม่
            folder_metadata = {
                'name': 'RoomMeterApp',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(f"Created folder with ID: {folder_id}")
        else:
            folder_id = items[0]['id']
            print(f"Found existing folder with ID: {folder_id}")
        
        # สร้างโฟลเดอร์ "RoomMeterPhoto" ภายใน "RoomMeterApp"
        photo_folder_id = None
        print("Searching for RoomMeterPhoto subfolder")
        results = drive_service.files().list(
            q=f"name='RoomMeterPhoto' and mimeType='application/vnd.google-apps.folder' and '{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print("Creating new RoomMeterPhoto subfolder")
            # สร้างโฟลเดอร์ย่อยใหม่
            photo_folder_metadata = {
                'name': 'RoomMeterPhoto',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [folder_id]
            }
            photo_folder = drive_service.files().create(body=photo_folder_metadata, fields='id').execute()
            photo_folder_id = photo_folder.get('id')
            print(f"Created photo folder with ID: {photo_folder_id}")
        else:
            photo_folder_id = items[0]['id']
            print(f"Found existing photo folder with ID: {photo_folder_id}")
        
        # ตรวจสอบว่ามี Sheets "RoomMeterData" ในโฟลเดอร์หรือไม่
        sheet_id = None
        print("Searching for RoomMeterData spreadsheet")
        results = drive_service.files().list(
            q=f"name='RoomMeterData' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print("Creating new RoomMeterData spreadsheet")
            # สร้าง Sheets ใหม่
            sheet_metadata = {
                'name': 'RoomMeterData',
                'mimeType': 'application/vnd.google-apps.spreadsheet',
                'parents': [folder_id]
            }
            sheet = drive_service.files().create(body=sheet_metadata, fields='id').execute()
            sheet_id = sheet.get('id')
            print(f"Created spreadsheet with ID: {sheet_id}")
            
            # สร้างชีทใหม่ที่มีชื่อชัดเจน
            body = {
                'requests': [
                    {
                        'addSheet': {
                            'properties': {
                                'title': 'Data',
                                'index': 0
                            }
                        }
                    }
                ]
            }
            
            # เพิ่มชีทใหม่
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=body
            ).execute()
            
            # ดึงข้อมูลชีตเพื่อเก็บ sheet ID
            sheet_metadata = sheets_service.spreadsheets().get(
                spreadsheetId=sheet_id
            ).execute()
            
            # เก็บ sheet ID ของชีต Data
            data_sheet_id = None
            for sheet in sheet_metadata.get('sheets', []):
                if sheet.get('properties', {}).get('title') == 'Data':
                    data_sheet_id = sheet.get('properties', {}).get('sheetId')
                    break
            
            # เก็บ sheet ID ลงใน session
            if data_sheet_id is not None:
                session['data_sheet_id'] = data_sheet_id
                print(f"Saved Data sheet ID: {data_sheet_id}")
            
            # สร้างคอลัมน์หัวตาราง
            try:
                print("Adding header row to spreadsheet")
                headers = [['วันที่เวลา', 'เลขห้อง', 'สถานะเลขห้อง', 'เลขมิเตอร์', 'สถานะเลขมิเตอร์', 
                          'เลขทศนิยม', 'สถานะเลขทศนิยม', 'เลขมิเตอร์เต็ม', 'ลิงก์รูปภาพ']]
                
                # ใช้ Range โดยระบุเป็น A1 notation แบบมี sheet name
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range="Data!A1:I1",
                    valueInputOption='RAW',
                    body={'values': headers}
                ).execute()
                print("Successfully added header row")
            except Exception as header_error:
                print(f"Error adding header row: {header_error}")

        else:
            sheet_id = items[0]['id']
            print(f"Found existing spreadsheet with ID: {sheet_id}")
            
            # ดึงข้อมูลชีตเพื่อเก็บ sheet ID
            sheet_metadata = sheets_service.spreadsheets().get(
                spreadsheetId=sheet_id
            ).execute()
            
            # เก็บ sheet ID ของชีตแรก (ใช้ชีตแรกเป็นหลัก ไม่ว่าจะชื่ออะไร)
            data_sheet_id = None
            for sheet in sheet_metadata.get('sheets', []):
                # ถ้ามีชีตชื่อ Data ให้ใช้ชีตนั้น
                if sheet.get('properties', {}).get('title') == 'Data':
                    data_sheet_id = sheet.get('properties', {}).get('sheetId')
                    break
                
            # ถ้าไม่มีชีตชื่อ Data ให้ใช้ชีตแรก
            if data_sheet_id is None and sheet_metadata.get('sheets'):
                data_sheet_id = sheet_metadata.get('sheets')[0].get('properties', {}).get('sheetId')
            
            # เก็บ sheet ID ลงใน session
            if data_sheet_id is not None:
                session['data_sheet_id'] = data_sheet_id
                print(f"Found and saved Data sheet ID: {data_sheet_id}")
        
        # บันทึกข้อมูลลงใน session
        if 'session' in globals() or 'session' in locals():
            session['folder_id'] = folder_id
            session['photo_folder_id'] = photo_folder_id
            session['sheet_id'] = sheet_id
            print("Saved folder and sheet IDs to session")
        
        return folder_id, sheet_id
        
    except HttpError as http_error:
        print(f"HTTP Error in create_user_resources: {http_error}")
        # ถ้าเป็น error เกี่ยวกับ authorization ให้ลบ session และให้ login ใหม่
        if http_error.resp.status in [401, 403]:
            print("Authorization error detected, clearing session")
            session.clear()
        return None, None
    except Exception as e:
        print(f"Error in create_user_resources: {e}")
        return None, None

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