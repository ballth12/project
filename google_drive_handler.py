class GoogleDriveHandler:
    """
    จัดการการอัปโหลดไฟล์ไปยัง Google Drive
    ใช้ decorator handle_auth_error
    """
    
    @staticmethod
    def upload_to_drive(processed_file_path, file_name, session_data, google_client):
        """
        อัปโหลดไฟล์ไปยัง Google Drive
        
        Args:
            processed_file_path: เส้นทางของไฟล์ที่จะอัปโหลด
            file_name: ชื่อที่จะใช้บน Google Drive
            session_data: ข้อมูลเซสชันที่มี credentials
            google_client: GoogleAPIClient instance
            
        Returns:
            dict: ข้อมูลการอัปโหลด หรือ None ถ้าไม่สำเร็จ
        """
        if not google_client:
            raise Exception("ไม่สามารถเชื่อมต่อกับ Google Drive ได้")
            
        # ใช้ photo_folder_id ถ้ามี มิฉะนั้นใช้ folder_id
        upload_folder_id = session_data.get('photo_folder_id', session_data.get('folder_id'))
        
        if not upload_folder_id:
            raise Exception("ไม่พบโฟลเดอร์สำหรับอัปโหลด")
        
        # อัปโหลดไฟล์
        return google_client.upload_to_drive(processed_file_path, upload_folder_id, file_name)
            
    @staticmethod
    def save_to_sheets(data, session_data, google_client):
        """
        บันทึกข้อมูลลงใน Google Sheets
        
        Args:
            data: ข้อมูลที่จะบันทึก
            session_data: ข้อมูลเซสชันที่มี credentials และ sheet_id
            google_client: GoogleAPIClient instance
            
        Returns:
            dict: ผลลัพธ์การบันทึก หรือ None ถ้าไม่สำเร็จ
        """
        if not google_client:
            raise Exception("ไม่สามารถเชื่อมต่อกับ Google Sheets ได้")
            
        # ตรวจสอบว่ามี sheet_id ในเซสชันหรือไม่
        if 'sheet_id' not in session_data:
            raise Exception("ไม่พบ Spreadsheet สำหรับบันทึกข้อมูล กรุณาล็อกอินใหม่")
            
        # บันทึกข้อมูล
        return google_client.save_to_sheets(session_data['sheet_id'], data, session_data)