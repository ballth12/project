# google_api_client.py - Google API Client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from flask import session
import os
import time

class GoogleAPIClient:
    """
    คลาสสำหรับจัดการการเชื่อมต่อกับ Google API
    """
    
    def __init__(self):
        """กำหนดค่าเริ่มต้น"""
        self.drive_service = None
        self.sheets_service = None
        self._build_services()
    
    def _build_services(self):
        """สร้าง Google API services จาก session credentials"""
        from google_auth import get_valid_credentials
        
        credentials = get_valid_credentials()
        if credentials:
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
    
    def upload_to_drive(self, file_path, folder_id, file_name=None):
        """
        อัปโหลดไฟล์ไปยัง Google Drive
        
        Args:
            file_path (str): เส้นทางไฟล์ที่จะอัปโหลด
            folder_id (str): ID ของโฟลเดอร์ใน Google Drive
            file_name (str, optional): ชื่อไฟล์ที่ต้องการ
            
        Returns:
            dict: ข้อมูลไฟล์ที่อัปโหลด
            
        Raises:
            Exception: เมื่อไม่สามารถอัปโหลดได้
        """
        if not self.drive_service:
            raise Exception("Google Drive Service ไม่พร้อมใช้งาน")
        
        actual_file_name = file_name or os.path.basename(file_path)
        file_metadata = {
            'name': actual_file_name,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return file
    
    def save_to_sheets(self, spreadsheet_id, values, session_data=None):
        """
        บันทึกข้อมูลลงใน Google Sheets
        
        Args:
            spreadsheet_id (str): ID ของ Spreadsheet
            values (list): ข้อมูลที่จะบันทึก
            session_data (dict, optional): ข้อมูล session
            
        Returns:
            dict: ผลลัพธ์การบันทึก
            
        Raises:
            Exception: เมื่อไม่สามารถบันทึกได้
        """
        if not self.sheets_service:
            raise Exception("Google Sheets Service ไม่พร้อมใช้งาน")
        
        # หาแถวว่างถัดไป
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="A:A"
        ).execute()

        values_list = result.get('values', [])
        next_row = len(values_list) + 1
        
        # ใช้ Grid API ถ้ามี data_sheet_id
        data_sheet_id = session_data.get('data_sheet_id') if session_data else None
        
        if data_sheet_id:
            # ใช้ batchUpdate สำหรับ performance ที่ดีกว่า
            update_body = {
                "requests": [{
                    "updateCells": {
                        "start": {
                            "sheetId": data_sheet_id,
                            "rowIndex": next_row - 1,  # 0-based index
                            "columnIndex": 0
                        },
                        "rows": [{
                            "values": [
                                {"userEnteredValue": {"stringValue": str(value)}} 
                                for value in values
                            ]
                        }],
                        "fields": "userEnteredValue"
                    }
                }]
            }
            
            return self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=update_body
            ).execute()
        else:
            # ใช้ A1 notation เป็น fallback
            body = {'values': [values]}
            
            return self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"A{next_row}",
                valueInputOption='RAW',
                body=body
            ).execute()

def create_user_resources(user_email):
    """
    สร้างโฟลเดอร์และ Sheets สำหรับผู้ใช้
    
    Args:
        user_email (str): อีเมลของผู้ใช้
        
    Returns:
        tuple: (folder_id, sheet_id)
    """
    from google_auth import get_valid_credentials
    
    credentials = get_valid_credentials()
    if not credentials:
        print("ไม่มี valid credentials")
        return None, None
    
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        sheets_service = build('sheets', 'v4', credentials=credentials)
        
        # สร้างหรือหาโฟลเดอร์หลัก
        folder_id = _create_or_find_folder(drive_service, 'RoomMeterApp')
        
        # สร้างหรือหาโฟลเดอร์รูปภาพ
        photo_folder_id = _create_or_find_folder(
            drive_service, 'RoomMeterPhoto', parent_id=folder_id
        )
        
        # สร้างหรือหา Spreadsheet
        sheet_id = _create_or_find_spreadsheet(
            drive_service, sheets_service, 'RoomMeterData', folder_id
        )
        
        # บันทึกลงใน session
        session['folder_id'] = folder_id
        session['photo_folder_id'] = photo_folder_id
        session['sheet_id'] = sheet_id
        
        return folder_id, sheet_id
        
    except Exception as e:
        print(f"Error in create_user_resources: {e}")
        return None, None

def _create_or_find_folder(drive_service, folder_name, parent_id=None):
    """สร้างหรือหาโฟลเดอร์"""
    # ค้นหาโฟลเดอร์ที่มีอยู่
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = drive_service.files().list(q=query, fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    
    # สร้างโฟลเดอร์ใหม่
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents'] = [parent_id]

    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def _create_or_find_spreadsheet(drive_service, sheets_service, sheet_name, folder_id):
    """สร้างหรือหา Spreadsheet"""
    # ค้นหา Spreadsheet ที่มีอยู่
    query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false"
    
    results = drive_service.files().list(q=query, fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if items:
        sheet_id = items[0]['id']
        _ensure_data_sheet(sheets_service, sheet_id)
        return sheet_id
    
    # สร้าง Spreadsheet ใหม่
    sheet_metadata = {
        'name': sheet_name,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'parents': [folder_id]
    }
    
    sheet = drive_service.files().create(body=sheet_metadata, fields='id').execute()
    sheet_id = sheet.get('id')
    
    # สร้างชีต Data และ header
    _setup_new_spreadsheet(sheets_service, sheet_id)
    
    return sheet_id

def _ensure_data_sheet(sheets_service, sheet_id):
    """ตรวจสอบและเก็บ Data sheet ID"""
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    
    for sheet in sheet_metadata.get('sheets', []):
        if sheet.get('properties', {}).get('title') == 'Data':
            session['data_sheet_id'] = sheet.get('properties', {}).get('sheetId')
            return
    
    # ใช้ชีตแรกถ้าไม่มีชีต Data
    if sheet_metadata.get('sheets'):
        session['data_sheet_id'] = sheet_metadata.get('sheets')[0].get('properties', {}).get('sheetId')

def _setup_new_spreadsheet(sheets_service, sheet_id):
    """ตั้งค่า Spreadsheet ใหม่"""
    # สร้างชีต Data
    body = {
        'requests': [{
            'addSheet': {
                'properties': {
                    'title': 'Data',
                    'index': 0
                }
            }
        }]
    }
    
    sheets_service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
    
    # เก็บ Data sheet ID
    _ensure_data_sheet(sheets_service, sheet_id)
    
    # เพิ่ม header
    headers = [['วันที่เวลา', 'เลขห้อง', 'สถานะเลขห้อง', 'เลขมิเตอร์', 'สถานะเลขมิเตอร์', 
               'เลขทศนิยม', 'สถานะเลขทศนิยม', 'เลขมิเตอร์เต็ม', 'ลิงก์รูปภาพ']]
    
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Data!A1:I1",
        valueInputOption='RAW',
        body={'values': headers}
    ).execute()