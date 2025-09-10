# app.py - ส่วนหลักที่ปรับปรุงแล้ว
from flask import Flask, request, render_template, jsonify, send_from_directory, redirect, session, url_for
import os
import time
import uuid
import threading
from dotenv import load_dotenv
from detector import ImageDetector
from google_auth import create_flow, login_required, handle_auth_error
from google_api_client import GoogleAPIClient, create_user_resources
from google_drive_handler import GoogleDriveHandler

# โหลดตัวแปรจากไฟล์ .env สำหรับการพัฒนาในเครื่อง
load_dotenv()

# สร้าง Flask App
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# สร้างโฟลเดอร์สำหรับเก็บไฟล์อัปโหลดชั่วคราว
UPLOAD_FOLDER = os.path.join(os.environ.get('TMPDIR', './'), 'uploads')
PROCESSED_FOLDER = os.path.join(os.environ.get('TMPDIR', './'), 'processed')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# สร้าง detector เพียงครั้งเดียว
detector = ImageDetector({
    'model_path': 'bestMR.pt',
    'use_gpu': True
})

# ฟังก์ชันสำหรับลบไฟล์หลังจาก delay
def schedule_file_cleanup(file_paths, delay_seconds=60):
    """
    กำหนดเวลาลบไฟล์หลังจาก delay_seconds วินาที
    
    Args:
        file_paths (list): รายการเส้นทางไฟล์ที่จะลบ
        delay_seconds (int): เวลาหน่วงก่อนลบไฟล์ (วินาที)
    """
    def cleanup_files():
        time.sleep(delay_seconds)
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🧹 Cleaned up file: {file_path}")
            except Exception as e:
                print(f"❌ Error cleaning up file {file_path}: {e}")
    
    # เริ่ม thread สำหรับลบไฟล์
    cleanup_thread = threading.Thread(target=cleanup_files)
    cleanup_thread.daemon = True  # ทำให้ thread หยุดเมื่อโปรแกรมหลักหยุด
    cleanup_thread.start()

@app.route('/')
def index():
    # ถ้ายังไม่ได้ล็อกอิน ให้ไปที่หน้าล็อกอิน
    if 'credentials' not in session:
        return redirect(url_for('login_page'))
    # ถ้าล็อกอินแล้ว ให้ไปที่หน้าหลัก
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/auth')
def auth():
    try:
        flow = create_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['state'] = state
        print(f"Redirecting to: {authorization_url}")
        return redirect(authorization_url)
    except Exception as e:
        print(f"Error in auth(): {e}")
        return f"เกิดข้อผิดพลาดในการล็อกอิน: {str(e)}"

@app.route('/callback')
def callback():
    try:
        # แสดงข้อมูล request เพื่อการแก้ไขปัญหา
        print(f"Callback URL: {request.url}")
        print(f"Headers: {request.headers}")
        
        flow = create_flow()
        
        # รองรับ Cloudflare
        authorization_response = request.url
        if request.headers.get('X-Forwarded-Proto') == 'https' and 'http://' in authorization_response:
            authorization_response = authorization_response.replace('http://', 'https://', 1)
            print(f"Modified authorization_response: {authorization_response}")
        
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        
        # เก็บ credentials ลงใน session
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        session.permanent = True
        
        # ตั้งค่าข้อมูลผู้ใช้เริ่มต้น
        session['user_email'] = 'default_user@example.com'
        session['user_name'] = 'Default User'
        
        # พยายามดึงข้อมูลผู้ใช้จาก People API
        try:
            # พยายามใช้ People API ถ้าเป็นไปได้
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            credentials_obj = Credentials(**session['credentials'])
            people_service = build('people', 'v1', credentials=credentials_obj)
            profile = people_service.people().get(
                resourceName='people/me',
                personFields='emailAddresses,names'
            ).execute()
            
            if 'emailAddresses' in profile:
                session['user_email'] = profile['emailAddresses'][0]['value']
            
            if 'names' in profile:
                session['user_name'] = profile['names'][0]['displayName']
        except Exception:
            pass  # ใช้ค่าเริ่มต้นถ้าดึงไม่ได้
        
        # สร้างโฟลเดอร์และ Sheets สำหรับผู้ใช้
        create_user_resources(session.get('user_email', 'unknown'))
        
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error in callback: {e}")
        return f"เกิดข้อผิดพลาดในการล็อกอิน: {str(e)}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/get_user_info')
@login_required
def get_user_info():
    # ดึงข้อมูลผู้ใช้จาก session
    user_info = {
        'name': session.get('user_name', 'ไม่ระบุชื่อ'),
        'email': session.get('user_email', 'ไม่ระบุอีเมล')
    }
    
    # เพิ่มลิงก์ Google Drive และ Sheets ถ้ามี folder_id และ sheet_id ใน session
    if 'folder_id' in session:
        # สร้าง URL สำหรับเปิดโฟลเดอร์
        user_info['folder_link'] = f"https://drive.google.com/drive/folders/{session['folder_id']}"
    
    # เพิ่มลิงก์โฟลเดอร์รูปภาพ
    if 'photo_folder_id' in session:
        user_info['photo_folder_link'] = f"https://drive.google.com/drive/folders/{session['photo_folder_id']}"
    
    if 'sheet_id' in session:
        # สร้าง URL สำหรับเปิด Sheets
        user_info['sheet_link'] = f"https://docs.google.com/spreadsheets/d/{session['sheet_id']}/?gid={session['data_sheet_id']}#gid={session['data_sheet_id']}"
    
    return jsonify(user_info)

@app.route('/processed/<filename>')
@login_required
def processed_file(filename):
    """ส่งไฟล์รูปที่ประมวลผลแล้ว"""
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

@app.route('/process', methods=['POST'])
@login_required
@handle_auth_error
def process():
    if 'file' not in request.files:
        return jsonify({'error': 'ไม่พบไฟล์ในการอัปโหลด'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'ไม่ได้เลือกไฟล์'})
    
    if file:
        # สร้างชื่อไฟล์แบบสุ่มเพื่อป้องกันการซ้ำกัน (สำหรับ temp storage)
        file_ext = os.path.splitext(file.filename)[1]
        temp_filename = str(uuid.uuid4()) + file_ext
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        
        # บันทึกไฟล์
        file.save(file_path)
        
        # ประมวลผลภาพ
        try:
            results = detector.process_image(file_path, app.config['PROCESSED_FOLDER'])
            
            files_to_cleanup = [file_path]
            if results.get('processed_image_path'):
                files_to_cleanup.append(results['processed_image_path'])
            
            # *** อัปโหลดไปยัง Google Drive เฉพาะเมื่อ can_upload = True ***
            # (ซึ่งหมายความว่าต้องเจอทั้งเลขห้องและเลขมิเตอร์)
            if results['can_upload'] and 'credentials' in session:
                try:
                    google_client = GoogleAPIClient()
                    file_info = GoogleDriveHandler.upload_to_drive(
                        results['processed_image_path'], 
                        temp_filename,
                        session, 
                        google_client
                    )
                    
                    if file_info:
                        # เก็บลิงก์ไฟล์ไว้ในผลลัพธ์
                        results['google_drive_link'] = file_info.get('webViewLink')
                        results['uploaded_filename'] = temp_filename
                        print(f"✅ อัปโหลดภาพสำเร็จ: {temp_filename}")
                    
                except Exception as e:
                    print(f"❌ ไม่สามารถอัปโหลดไฟล์ไปยัง Google Drive: {str(e)}")
                    # ไม่ throw error - ให้ผู้ใช้ดำเนินการต่อได้
            
            # *** กำหนดเวลาลบไฟล์หลังจาก 60 วินาที ***
            schedule_file_cleanup(files_to_cleanup, delay_seconds=60)
            print(f"⏰ Scheduled cleanup for {len(files_to_cleanup)} files in 60 seconds")
            
            return jsonify(results)
            
        except Exception as e:
            # ลบไฟล์ทันทีถ้าเกิดข้อผิดพลาด
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🧹 Cleaned up file immediately due to error: {file_path}")
            except:
                pass
            return jsonify({'error': f'เกิดข้อผิดพลาดในการประมวลผล: {str(e)}'})

@app.route('/save-to-sheets', methods=['POST'])
@login_required
@handle_auth_error
def save_to_sheets():
    try:
        # รับข้อมูลจาก frontend
        data = request.json

        # *** ตรวจสอบว่ามีข้อมูลครบถ้วน (ต้องมีทั้งเลขห้องและเลขมิเตอร์) ***
        if not data or not data.get('room_number') or not data.get('meter_number'):
            return jsonify({'error': 'ต้องมีทั้งเลขห้องและเลขมิเตอร์จึงจะสามารถบันทึกได้'})

        # ดึงข้อมูลที่แก้ไขแล้วและสถานะการแก้ไข
        room_number = data.get('room_number', '')
        room_edited = data.get('room_edited', False)
        meter_number = data.get('meter_number', '')
        meter_edited = data.get('meter_edited', False)
        decimal_number = data.get('decimal_number', '')
        decimal_edited = data.get('decimal_edited', False)
        full_meter = data.get('full_meter', '')
        google_drive_link = data.get('google_drive_link', 'ไม่มีลิงก์')
        
        # ตรวจสอบอีกครั้งว่าข้อมูลหลักไม่ว่าง
        if not room_number.strip() or not meter_number.strip():
            return jsonify({'error': 'เลขห้องและเลขมิเตอร์ต้องไม่ว่าง'})

        # กำหนดสถานะการแก้ไขเป็นข้อความ
        room_edited_status = "แก้ไขแล้ว" if room_edited else "ไม่ได้แก้ไข"
        meter_edited_status = "แก้ไขแล้ว" if meter_edited else "ไม่ได้แก้ไข"
        decimal_edited_status = "แก้ไขแล้ว" if decimal_edited else "ไม่ได้แก้ไข"

        # จัดเตรียมข้อมูลเพื่อบันทึกลงใน Sheets
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        sheet_data = [
            current_time,
            room_number,
            room_edited_status,
            meter_number,
            meter_edited_status,
            decimal_number,
            decimal_edited_status,
            full_meter,
            google_drive_link
        ]

        # บันทึกข้อมูล
        google_client = GoogleAPIClient()
        result = GoogleDriveHandler.save_to_sheets(sheet_data, session, google_client)

        if result:
            print(f"✅ บันทึกข้อมูลสำเร็จ: ห้อง {room_number}, มิเตอร์ {full_meter}")
            return jsonify({
                'success': True,
                'message': 'บันทึกข้อมูลเรียบร้อยแล้ว'
            })
        else:
            return jsonify({'error': 'เกิดข้อผิดพลาดในการบันทึกข้อมูล'})

    except Exception as e:
        print(f"Error in save_to_sheets: {e}")
        # ตรวจสอบว่าเป็น auth error หรือไม่
        if "credentials" in str(e).lower() or "authorization" in str(e).lower():
            return jsonify({'error': 'การเข้าสู่ระบบหมดอายุ กรุณาเข้าสู่ระบบใหม่', 'auth_error': True})
        return jsonify({'error': f'เกิดข้อผิดพลาดในการบันทึกข้อมูล: {str(e)}'})

if __name__ == '__main__':
    # ใช้พอร์ตจากสภาพแวดล้อมถ้ามี มิฉะนั้นใช้พอร์ต 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=True)