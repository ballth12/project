# google_drive_handler.py (ปรับปรุงแล้ว)
from flask import session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class GoogleDriveHandler:
    """
    จัดการการอัปโหลดไฟล์ไปยัง Google Drive (ปรับปรุงแล้ว)
    """
    
    @staticmethod
    def upload_to_drive(file_path, file_name, session_data, google_client):
        """
        อัปโหลดไฟล์ไปยัง Google Drive พร้อม Error Handling ที่ดีขึ้น
        
        Args:
            file_path: เส้นทางของไฟล์ที่จะอัปโหลด
            file_name: ชื่อที่จะใช้บน Google Drive
            session_data: ข้อมูลเซสชันที่มี credentials
            google_client: GoogleAPIClient instance
            
        Returns:
            dict: ข้อมูลการอัปโหลด หรือ None ถ้าไม่สำเร็จ
        """
        if not google_client:
            print("ไม่สามารถเชื่อมต่อกับ Google Drive ได้")
            return None
            
        try:
            # ใช้ photo_folder_id ถ้ามี มิฉะนั้นใช้ folder_id
            upload_folder_id = session_data.get('photo_folder_id', session_data.get('folder_id'))
            
            if not upload_folder_id:
                raise Exception("ไม่พบโฟลเดอร์สำหรับอัปโหลด")
            
            # อัปโหลดไฟล์ไปยัง Google Drive พร้อม file_name parameter
            file_info = google_client.upload_to_drive(file_path, upload_folder_id, file_name)
            
            return file_info
            
        except HttpError as http_error:
            status_code = http_error.resp.status
            if status_code in [401, 403]:
                print(f"Authorization error during upload: {http_error}")
                raise Exception(f"The credentials do not contain the necessary fields need to refresh the access token. กรุณาเข้าสู่ระบบใหม่")
            else:
                print(f"HTTP Error during upload: {http_error}")
                raise Exception(f"ไม่สามารถอัปโหลดไฟล์ไปยัง Google Drive: {str(http_error)}")
        except Exception as e:
            error_message = str(e)
            print(f"ไม่สามารถอัปโหลดไฟล์ไปยัง Google Drive: {error_message}")
            
            # ถ้าเป็น credential error ให้ throw exception พิเศษ
            if "credentials" in error_message.lower() or "refresh" in error_message.lower():
                raise Exception("The credentials do not contain the necessary fields need to refresh the access token. กรุณาเข้าสู่ระบบใหม่")
            else:
                raise Exception(f"ไม่สามารถอัปโหลดไฟล์ไปยัง Google Drive: {error_message}")
            
    @staticmethod
    def save_to_sheets(data, session_data, google_client):
        """
        บันทึกข้อมูลลงใน Google Sheets พร้อม Error Handling ที่ดีขึ้น
        
        Args:
            data: ข้อมูลที่จะบันทึก
            session_data: ข้อมูลเซสชันที่มี credentials และ sheet_id
            google_client: GoogleAPIClient instance
            
        Returns:
            dict: ผลลัพธ์การบันทึก หรือ None ถ้าไม่สำเร็จ
        """
        if not google_client:
            print("ไม่สามารถเชื่อมต่อกับ Google Sheets ได้")
            return None
            
        try:
            # ตรวจสอบว่ามี sheet_id ในเซสชันหรือไม่
            if 'sheet_id' not in session_data:
                raise Exception("ไม่พบ Spreadsheet สำหรับบันทึกข้อมูล กรุณาล็อกอินใหม่")
                
            # บันทึกข้อมูลลงใน Google Sheets พร้อมส่ง session_data
            result = google_client.save_to_sheets(session_data['sheet_id'], data, session_data)
            
            return result
            
        except HttpError as http_error:
            status_code = http_error.resp.status
            if status_code in [401, 403]:
                print(f"Authorization error during sheets save: {http_error}")
                raise Exception("The credentials do not contain the necessary fields need to refresh the access token. กรุณาเข้าสู่ระบบใหม่")
            else:
                print(f"HTTP Error during sheets save: {http_error}")
                raise Exception(f"ไม่สามารถบันทึกข้อมูลลงใน Google Sheets: {str(http_error)}")
        except Exception as e:
            error_message = str(e)
            print(f"ไม่สามารถบันทึกข้อมูลลงใน Google Sheets: {error_message}")
            
            # ถ้าเป็น credential error ให้ throw exception พิเศษ
            if "credentials" in error_message.lower() or "refresh" in error_message.lower():
                raise Exception("The credentials do not contain the necessary fields need to refresh the access token. กรุณาเข้าสู่ระบบใหม่")
            else:
                raise Exception(f"ไม่สามารถบันทึกข้อมูลลงใน Google Sheets: {error_message}")
    
    @staticmethod
    def check_credentials_health(session_data):
        """
        ตรวจสอบสุขภาพของ credentials
        
        Args:
            session_data: ข้อมูลเซสชัน
            
        Returns:
            dict: สถานะของ credentials
        """
        if 'credentials' not in session_data:
            return {'healthy': False, 'reason': 'No credentials in session'}
        
        try:
            from google.oauth2.credentials import Credentials
            credentials = Credentials(**session_data['credentials'])
            
            if not credentials.valid:
                if credentials.expired and credentials.refresh_token:
                    return {'healthy': False, 'reason': 'Expired but can refresh', 'can_refresh': True}
                else:
                    return {'healthy': False, 'reason': 'Invalid and cannot refresh', 'can_refresh': False}
            
            return {'healthy': True, 'reason': 'Valid credentials'}
            
        except Exception as e:
            return {'healthy': False, 'reason': f'Error checking credentials: {str(e)}', 'can_refresh': False}