from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import os
import time
from google.auth.transport.requests import Request

class GoogleAPIClient:
    """
    คลาสสำหรับจัดการการเชื่อมต่อกับ Google API (ปรับปรุงแล้ว)
    รองรับทั้งการเชื่อมต่อแบบ Service Account และ OAuth พร้อม Auto Token Refresh
    """
    
    def __init__(self, credentials_file=None, oauth_credentials=None):
        """
        กำหนดค่าเริ่มต้นสำหรับ Google API Client
        
        Args:
            credentials_file (str, optional): ไฟล์ Service Account credentials
            oauth_credentials (dict, optional): OAuth credentials จาก session
        """
        self.drive_service = None
        self.sheets_service = None
        self.credentials = None
        self.oauth_credentials_dict = oauth_credentials
        
        # ตรวจสอบว่าจะใช้ OAuth หรือ Service Account
        if oauth_credentials:
            try:
                self.credentials = Credentials(**oauth_credentials)
                self._ensure_valid_credentials()
                self._build_services()
            except Exception as e:
                print(f"Error initializing OAuth credentials: {e}")
                
        elif credentials_file and os.path.exists(credentials_file):
            # ใช้ Service Account
            try:
                self.credentials = ServiceAccountCredentials.from_service_account_file(
                    credentials_file,
                    scopes=[
                        'https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/spreadsheets'
                    ]
                )
                self._build_services()
            except Exception as e:
                print(f"Error initializing Google API Client with Service Account: {e}")
    
    def _ensure_valid_credentials(self):
        """
        ตรวจสอบและต่ออายุ credentials ถ้าจำเป็น
        """
        if not self.credentials:
            return False
        
        try:
            # ตรวจสอบว่า credentials หมดอายุหรือไม่
            if self.credentials.expired and self.credentials.refresh_token:
                print("Credentials expired, refreshing...")
                self.credentials.refresh(Request())
                
                # อัปเดต oauth_credentials_dict ด้วยข้อมูลใหม่
                if self.oauth_credentials_dict:
                    self.oauth_credentials_dict.update({
                        'token': self.credentials.token,
                        'refresh_token': self.credentials.refresh_token,
                        'token_uri': self.credentials.token_uri,
                        'client_id': self.credentials.client_id,
                        'client_secret': self.credentials.client_secret,
                        'scopes': self.credentials.scopes
                    })
                
                print("Credentials refreshed successfully")
                return True
            elif not self.credentials.valid:
                print("Credentials are not valid and cannot be refreshed")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error ensuring valid credentials: {e}")
            return False
    
    def _build_services(self):
        """
        สร้าง Google API services
        """
        try:
            if self.credentials:
                self.drive_service = build('drive', 'v3', credentials=self.credentials)
                self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
        except Exception as e:
            print(f"Error building Google API services: {e}")
    
    def _execute_with_retry(self, api_call, max_retries=3):
        """
        Execute API call with automatic retry on auth errors
        
        Args:
            api_call: ฟังก์ชันที่จะเรียก API
            max_retries: จำนวนครั้งสูงสุดที่จะลองใหม่
            
        Returns:
            ผลลัพธ์จาก API call หรือ raise exception
        """
        for attempt in range(max_retries):
            try:
                # ตรวจสอบ credentials ก่อนเรียก API
                if not self._ensure_valid_credentials():
                    raise Exception("Cannot ensure valid credentials")
                
                # Rebuild services if needed
                if not self.drive_service or not self.sheets_service:
                    self._build_services()
                
                # เรียก API
                return api_call()
                
            except HttpError as http_error:
                status_code = http_error.resp.status
                
                # ถ้าเป็น authorization error (401, 403) ให้ลองต่ออายุ token
                if status_code in [401, 403] and attempt < max_retries - 1:
                    print(f"Authorization error (attempt {attempt + 1}): {http_error}")
                    
                    # พยายามต่ออายุ credentials
                    if self.credentials and self.credentials.refresh_token:
                        try:
                            self.credentials.refresh(Request())
                            self._build_services()
                            print("Credentials refreshed, retrying...")
                            continue
                        except Exception as refresh_error:
                            print(f"Failed to refresh credentials: {refresh_error}")
                    
                    # ถ้าไม่สามารถต่ออายุได้ ให้ raise error
                    if attempt == max_retries - 1:
                        raise Exception(f"Authorization failed after {max_retries} attempts: {http_error}")
                
                # ถ้าเป็น error อื่นๆ ให้ raise ทันที
                else:
                    raise http_error
                    
            except Exception as e:
                # ถ้าเป็น error อื่นๆ ที่ไม่ใช่ HttpError
                if attempt == max_retries - 1:
                    raise e
                else:
                    print(f"Error in API call (attempt {attempt + 1}): {e}")
                    time.sleep(1)  # รอ 1 วินาทีก่อนลองใหม่
    
    def upload_to_drive(self, file_path, folder_id, file_name=None):
        """
        อัปโหลดไฟล์ไปยัง Google Drive พร้อม Auto Retry
        
        Args:
            file_path (str): เส้นทางไฟล์ที่จะอัปโหลด
            folder_id (str): ID ของโฟลเดอร์ใน Google Drive
            file_name (str, optional): ชื่อไฟล์ที่ต้องการ (ถ้าไม่ระบุจะใช้ชื่อจากไฟล์)
            
        Returns:
            dict: ข้อมูลไฟล์ที่อัปโหลด
        """
        if not self.drive_service:
            raise Exception("Google Drive Service is not initialized")
        
        def _upload():
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
        
        return self._execute_with_retry(_upload)
    
    def save_to_sheets(self, spreadsheet_id, values, session_data=None):
        """
        บันทึกข้อมูลลงใน Google Sheets โดยใช้ Grid API แทน A1 notation พร้อม Auto Retry
        
        Args:
            spreadsheet_id (str): ID ของ Spreadsheet
            values (list): ข้อมูลที่จะบันทึก
            session_data (dict, optional): ข้อมูล session ที่มี data_sheet_id
            
        Returns:
            dict: ผลลัพธ์การบันทึก
        """
        if not self.sheets_service:
            raise Exception("Google Sheets Service is not initialized")
        
        def _save_to_sheets():
            # 1. หาแถวว่างถัดไปโดยดูจำนวนข้อมูลในคอลัมน์ A
            try:
                # ดึง data_sheet_id จาก session_data ถ้ามี
                data_sheet_id = None
                if session_data:
                    data_sheet_id = session_data.get('data_sheet_id')
                
                # ถ้าไม่มี data_sheet_id ในเซสชัน ให้ดึงข้อมูลชีตเอง
                if not data_sheet_id:
                    # ดึงข้อมูลของ spreadsheet เพื่อหา sheet ID ของชีตแรก
                    sheet_metadata = self.sheets_service.spreadsheets().get(
                        spreadsheetId=spreadsheet_id
                    ).execute()
                    
                    # ใช้ชีตแรกถ้าไม่สามารถหา data_sheet_id ได้
                    if sheet_metadata.get('sheets'):
                        data_sheet_id = sheet_metadata.get('sheets')[0].get('properties', {}).get('sheetId')
                
                # ดึงข้อมูลคอลัมน์ A ทั้งหมดเพื่อหาแถวสุดท้าย
                result = self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range="A:A"  # ใช้ A:A โดยไม่ระบุชื่อชีต ซึ่งจะใช้ชีตแรกโดยอัตโนมัติ
                ).execute()
                
                values_list = result.get('values', [])
                next_row = len(values_list) + 1
                
                # 2. ใช้ API แบบ Grid-based ในการอัปเดตข้อมูล (ซึ่งไม่ขึ้นกับชื่อชีต)
                # ถ้ามี data_sheet_id จากเซสชัน
                if data_sheet_id:
                    # ใช้ batchUpdate API ที่ไม่ขึ้นกับชื่อชีต
                    update_body = {
                        "requests": [
                            {
                                "updateCells": {
                                    "start": {
                                        "sheetId": data_sheet_id,
                                        "rowIndex": next_row - 1,  # row indices are 0-based
                                        "columnIndex": 0
                                    },
                                    "rows": [
                                        {
                                            "values": [{"userEnteredValue": {"stringValue": str(value)}} for value in values]
                                        }
                                    ],
                                    "fields": "userEnteredValue"
                                }
                            }
                        ]
                    }
                    
                    result = self.sheets_service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body=update_body
                    ).execute()
                    
                    return result
                
                # หากไม่มี data_sheet_id ให้ใช้วิธีอัปเดตด้วย range โดยไม่ต้องระบุชื่อชีต
                # ซึ่งจะใช้ชีตแรกโดยอัตโนมัติ (จะทำงานไม่ว่าชีตจะชื่ออะไร)
                else:
                    body = {
                        'values': [values]
                    }
                    
                    result = self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"A{next_row}",  # ใช้เพียง A{next_row} โดยไม่ระบุชื่อชีต
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    
                    return result
                    
            except Exception as e:
                print(f"Error saving to sheets: {e}")
                # ถ้าเกิดข้อผิดพลาด ให้ลองใช้วิธีดั้งเดิม (ซึ่งอาจทำงานได้กับบางเวอร์ชัน)
                try:
                    # ตั้งค่าเริ่มต้นที่แถว 2 (หลังหัวตาราง)
                    next_row = 2
                    
                    body = {
                        'values': [values]
                    }
                    
                    # พยายามอัปเดตโดยไม่ระบุชื่อชีต (จะใช้ชีตแรกโดยอัตโนมัติ)
                    result = self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"A{next_row}",
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    
                    return result
                except Exception as backup_error:
                    raise Exception(f"Failed to save data to sheets: {backup_error}")
        
        return self._execute_with_retry(_save_to_sheets)
    
    def get_file_web_link(self, file_id):
        """
        ดึงลิงก์สำหรับเปิดไฟล์บนเว็บ พร้อม Auto Retry
        
        Args:
            file_id (str): ID ของไฟล์
            
        Returns:
            str: ลิงก์สำหรับเปิดไฟล์
        """
        if not self.drive_service:
            raise Exception("Google Drive Service is not initialized")
        
        def _get_link():
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file.get('webViewLink', '')
        
        return self._execute_with_retry(_get_link)
        
    def get_folder_web_link(self, folder_id):
        """
        ดึงลิงก์สำหรับเปิดโฟลเดอร์บนเว็บ
        
        Args:
            folder_id (str): ID ของโฟลเดอร์
            
        Returns:
            str: ลิงก์สำหรับเปิดโฟลเดอร์
        """
        return f"https://drive.google.com/drive/folders/{folder_id}"
    
    def get_updated_credentials(self):
        """
        ดึง credentials ที่อัปเดตแล้ว (สำหรับอัปเดต session)
        
        Returns:
            dict: credentials ที่อัปเดตแล้ว
        """
        if self.oauth_credentials_dict and self.credentials:
            return self.oauth_credentials_dict
        return None