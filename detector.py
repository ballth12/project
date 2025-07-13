# improved_detector.py
import os
import cv2
import re
import time
import numpy as np
from ultralytics import YOLO
import easyocr
import math
from concurrent.futures import ThreadPoolExecutor
import uuid

class ImageDetector:
    def __init__(self, models_config=None):
        """
        กำหนดค่าเริ่มต้นสำหรับตัวตรวจจับรูปภาพ
        
        Args:
            models_config (dict, optional): ค่า configuration ของโมเดล
        """
        if models_config is None:
            models_config = {
                'model_path': 'bestMR.pt',  # เปลี่ยนเป็น model เดียว
                'use_gpu': True
            }
        
        # เริ่มจับเวลา
        start_time = time.time()
        
        # กำหนดค่าพารามิเตอร์
        self.CONF_THRESHOLD = 0.6
        self.EXPECTED_ROOM_LENGTH = [3, 4]  # ความยาวตัวเลขห้องที่คาดหวัง
        self.EXPECTED_METER_LENGTH = [4, 5, 6, 7]  # ความยาวตัวเลขมิเตอร์ที่คาดหวัง
        self.EXPECTED_DECIMAL_LENGTH = [1]  # ความยาวตัวเลขทศนิยมที่คาดหวัง
        self.ROOM_PATTERN = r'^\d{3,4}$'  # รูปแบบเลขห้องปกติ (3-4 หลัก)
        self.METER_PATTERN = r'^\d{4,7}$'  # รูปแบบเลขมิเตอร์ปกติ (4-7 หลัก)
        self.DECIMAL_PATTERN = r'^\d{1}$'  # รูปแบบเลขทศนิยมปกติ (1 หลัก)
        
        # กำหนด class mapping
        self.CLASS_MAP = {
            0: 'meter',     # เลขมิเตอร์จำนวนเต็ม
            1: 'meter1',    # เลขมิเตอร์หลักทศนิยม
            2: 'roomN'      # เลขห้อง
        }
        
        # โหลดโมเดล YOLO เดียว
        print("กำลังโหลดโมเดล YOLO...")
        self.unified_model = YOLO(models_config['model_path'])
        
        # โหลด EasyOCR
        print("กำลังโหลด EasyOCR...")
        self.reader = easyocr.Reader(['en'], gpu=models_config.get('use_gpu', True), quantize=False)
        
        # สีสำหรับ bounding box
        self.colors = {
            'roomN': (255, 0, 0),    # สีแดง
            'meter': (0, 255, 0),    # สีเขียว
            'meter1': (0, 0, 255)    # สีน้ำเงิน
        }
        
        # Cache CLAHE objects
        self.clahe_enhance = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        self.clahe_ocr = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        # จบการจับเวลา
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"โหลดโมเดลและเตรียมระบบเสร็จสิ้น (ใช้เวลา {elapsed_time:.2f} วินาที)")

    def enhance_contrast(self, img):
        """เพิ่มความคมชัดให้กับรูปภาพโดยใช้ CLAHE ที่ cache ไว้"""
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        cl = self.clahe_enhance.apply(l)  # ใช้ cached CLAHE object
        enhanced_lab = cv2.merge((cl, a, b))
        enhanced_img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        return enhanced_img

    def preprocess_for_ocr(self, img):
        """ตัดสัญญาณรบกวนและปรับปรุงคุณภาพรูปภาพสำหรับ OCR"""
        # เก็บรายการภาพที่ประมวลผล
        processed_images = []
        
        # 1. ภาพต้นฉบับที่เพิ่มความคมชัด
        enhanced = self.enhance_contrast(img)
        processed_images.append(("original_enhanced", enhanced))
        
        # 2. เปลี่ยนเป็นภาพเทา
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_images.append(("gray", gray))
        
        # 3. ปรับสมดุลแสงด้วย CLAHE (ใช้ cached object)
        clahe_img = self.clahe_ocr.apply(gray)
        processed_images.append(("clahe", clahe_img))
        
        # 4. ปรับขนาดภาพให้ใหญ่ขึ้น 2 เท่า
        height, width = gray.shape
        enlarged = cv2.resize(gray, (width*2, height*2), interpolation=cv2.INTER_CUBIC)
        processed_images.append(("enlarged", enlarged))
        
        # 5. ปรับความสว่าง/คอนทราสต์
        adjusted = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)
        processed_images.append(("adjusted", adjusted))
        
        # 6. กำจัดสัญญาณรบกวน
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        processed_images.append(("denoised", denoised))
        
        # 7. เทรชโฮลด์แบบ Otsu
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(("otsu", otsu))
        
        # 8. เทรชโฮลด์แบบ Adaptive
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        processed_images.append(("adaptive", adaptive_thresh))
        
        # 9. เทรชโฮลด์แบบทั่วไป
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        processed_images.append(("binary", binary))
        
        # 10. ลบพื้นหลังและปรับคอนทราสต์
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        processed_images.append(("bg_removed", thresh))
        
        # 11. ลองหมุนภาพเล็กน้อยเพื่อแก้การเอียง
        for angle in [-3, -1, 1, 3]:
            h, w = gray.shape
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(gray, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC, 
                                    borderMode=cv2.BORDER_REPLICATE)
            processed_images.append((f"rotated_{angle}", rotated))
        
        return processed_images

    def perform_ocr(self, img_name, img, is_decimal=False):
        """ทำ OCR กับภาพหนึ่งภาพ และคืนผลลัพธ์"""
        
        # ทดลองปรับพารามิเตอร์ EasyOCR หลายแบบ
        ocr_results = []
        
        # ทดลอง 1: ตั้งค่าพื้นฐานที่ปรับปรุงแล้ว
        try:
            result1 = self.reader.readtext(
                img, 
                detail=1, 
                allowlist='0123456789',
                paragraph=False, 
                height_ths=0.8,
                width_ths=0.7,
                y_ths=0.5,
                x_ths=1.0,
                add_margin=0.1,
                text_threshold=0.5,
                low_text=0.3,
                link_threshold=0.3
            )
            for detection in result1:
                bbox, text, conf = detection
                if conf > 0.1:
                    ocr_results.append((text, conf, f"{img_name}_base"))
        except Exception as e:
            pass
        
        # ทดลอง 2: เน้นการอ่านตัวเลขแบบแยกส่วน
        try:
            result2 = self.reader.readtext(
                img, 
                detail=1, 
                allowlist='0123456789', 
                paragraph=False, 
                contrast_ths=0.1,
                adjust_contrast=0.5,
                height_ths=0.5,
                width_ths=0.5,
                add_margin=0.2,
                text_threshold=0.4,
                low_text=0.2,
                mag_ratio=6.0 if is_decimal else 1.5  # ปรับ mag_ratio เฉพาะ decimal
            )
            for detection in result2:
                bbox, text, conf = detection
                if conf > 0.1:
                    ocr_results.append((text, conf, f"{img_name}_segment"))
        except Exception as e:
            pass
        
        # ทดลอง 3: การตั้งค่าสำหรับตัวเลขที่ชัดเจน
        try:
            result3 = self.reader.readtext(
                img, 
                detail=1, 
                allowlist='0123456789',
                paragraph=False,
                min_size=5,
                text_threshold=0.7,
                low_text=0.5,
                link_threshold=0.5,
                canvas_size=1280,
                mag_ratio=4.0 if is_decimal else 1.0,  # ปรับ mag_ratio เฉพาะ decimal
                slope_ths=0.2,
                ycenter_ths=0.5,
                height_ths=0.5,
                width_ths=0.5,
                add_margin=0.1,
                x_ths=1.5,
                y_ths=0.5
            )
            for detection in result3:
                bbox, text, conf = detection
                if conf > 0.15:
                    ocr_results.append((text, conf, f"{img_name}_clear"))
        except Exception as e:
            pass
        
        # ทดลอง 4: การตั้งค่าสำหรับตัวเลขที่จางหรือเบลอ
        try:
            result4 = self.reader.readtext(
                img, 
                detail=1, 
                allowlist='0123456789',
                paragraph=False,
                text_threshold=0.3,
                low_text=0.1,
                link_threshold=0.2,
                canvas_size=3840,
                mag_ratio=12.0 if is_decimal else 3.0,  # ปรับ mag_ratio เฉพาะ decimal
                contrast_ths=0.05,
                adjust_contrast=0.3,
                height_ths=0.3,
                width_ths=0.3,
                add_margin=0.3,
                x_ths=2.0,
                y_ths=0.3
            )
            for detection in result4:
                bbox, text, conf = detection
                if conf > 0.05:
                    ocr_results.append((text, conf, f"{img_name}_blur"))
        except Exception as e:
            pass
        
        return ocr_results

    def filter_and_select_best_result(self, all_ocr_results, expected_lengths=None, pattern=None):
        """กรองและเลือกผลลัพธ์ OCR ที่ดีที่สุด"""
        if not all_ocr_results:
            return None
        
        # จัดกลุ่มผลลัพธ์ตามความยาว
        results_by_length = {}
        for text, conf, method in all_ocr_results:
            cleaned_text = ''.join(re.findall(r'\d+', text))  #**************************************
            if cleaned_text:  # ถ้ามีตัวเลข
                length = len(cleaned_text)
                if length not in results_by_length:
                    results_by_length[length] = []
                results_by_length[length].append((cleaned_text, conf, method))
        
        # ค้นหาความยาวที่พบบ่อยที่สุด
        if results_by_length:
            # ให้น้ำหนักกับความยาวที่คาดหวัง
            preferred_length = None
            if expected_lengths:
                for length in expected_lengths:
                    if length in results_by_length:
                        preferred_length = length
                        break
            
            # ถ้าไม่มีความยาวที่คาดหวัง ให้เลือกความยาวที่มีผลลัพธ์มากที่สุด
            if not preferred_length:
                length_counts = []
                for length, results in results_by_length.items():
                    count = len(results)
                    length_counts.append((length, count))
                length_counts.sort(key=lambda x: x[1], reverse=True)
                preferred_length = length_counts[0][0]
            
            # เลือกผลลัพธ์ที่มี confidence สูงสุดจากความยาวที่เลือก
            candidates = results_by_length[preferred_length]
            
            # ถ้ามีผลลัพธ์ที่ซ้ำกัน ให้นับความถี่
            text_frequency = {}
            for text, conf, method in candidates:
                if text not in text_frequency:
                    text_frequency[text] = {'count': 0, 'max_conf': 0, 'method': method}
                text_frequency[text]['count'] += 1
                text_frequency[text]['max_conf'] = max(text_frequency[text]['max_conf'], conf)
                # print(f"{text_frequency}{method}")
            
            # เลือกตัวเลขที่พบบ่อยที่สุดและมี confidence สูง
            best_text = None
            best_score = 0
            best_method = None
            best_conf = 0
            
            for text, info in text_frequency.items():
                # print(text)
                # print(info)
                # print("--------------------------------")
                # คะแนน = (ความถี่ * 0.3) + (confidence * 0.7)
                score = (info['count'] * 0.3) + (info['max_conf'] * 0.7)
                
                # เพิ่มคะแนนถ้าตรงกับรูปแบบที่กำหนด
                if pattern and re.match(pattern, text):
                    score += 0.2
                
                if score > best_score:
                    best_score = score
                    best_text = text
                    best_method = info['method']
                    best_conf = info['max_conf']
            
            if best_text:
                return (best_text, best_conf, best_method)
        
        # ถ้าไม่มีผลลัพธ์ที่ดี ใช้ตัวที่มี confidence สูงสุด
        all_ocr_results.sort(key=lambda x: x[1], reverse=True)
        text, conf, method = all_ocr_results[0]
        cleaned_text = ''.join(re.findall(r'\d+', text))
        return (cleaned_text, conf, method) if cleaned_text else None

    def get_detections_by_class(self, img):
        """ตรวจจับทุก bounding box และแยกตาม class"""
        results = self.unified_model(img)
        boxes = results[0].boxes.xyxy.cpu().numpy()
        confidences = results[0].boxes.conf.cpu().numpy()
        classes = results[0].boxes.cls.cpu().numpy()
        
        # แยกการตรวจจับตาม class
        detections_by_class = {
            'roomN': [],
            'meter': [],
            'meter1': []
        }
        
        for j, (box, conf, cls) in enumerate(zip(boxes, confidences, classes)):
            if conf >= self.CONF_THRESHOLD:
                class_name = self.CLASS_MAP.get(int(cls))
                if class_name:
                    x1, y1, x2, y2 = map(int, box)
                    cropped_img = img[y1:y2, x1:x2]
                    
                    if cropped_img.shape[0] < 15 or cropped_img.shape[1] < 15:
                        continue
                    
                    # กำหนดพารามิเตอร์สำหรับแต่ละ class
                    if class_name == 'roomN':
                        expected_lengths = self.EXPECTED_ROOM_LENGTH
                        pattern = self.ROOM_PATTERN
                        is_decimal = False
                    elif class_name == 'meter':
                        expected_lengths = self.EXPECTED_METER_LENGTH
                        pattern = self.METER_PATTERN
                        is_decimal = False
                    elif class_name == 'meter1':
                        expected_lengths = self.EXPECTED_DECIMAL_LENGTH
                        pattern = self.DECIMAL_PATTERN
                        is_decimal = True
                    
                    # ประมวลผลภาพหลายรูปแบบ
                    processed_images = self.preprocess_for_ocr(cropped_img)
                    
                    # ทำ OCR แบบขนาน
                    all_ocr_results = []
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        futures = [executor.submit(self.perform_ocr, img_name, img, is_decimal) 
                                 for img_name, img in processed_images]
                        for  future in futures:
                            ocr_results = future.result()
                            if ocr_results:
                                all_ocr_results.extend(ocr_results)
                    
                    # เลือกผลลัพธ์ที่ดีที่สุด
                    best_result_data = self.filter_and_select_best_result(
                        all_ocr_results, expected_lengths, pattern)
                    
                    if best_result_data:
                        number, number_conf, method = best_result_data
                        
                        # คำนวณจุดกึ่งกลางของ bounding box
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        
                        detection_data = {
                            'number': number,
                            'confidence': number_conf,
                            'method': method,
                            'box': [x1, y1, x2, y2],
                            'center': (center_x, center_y),
                            'detection_confidence': conf,
                            'class': class_name
                        }
                        
                        detections_by_class[class_name].append(detection_data)
        
        return detections_by_class

    def calculate_distance(self, point1, point2):
        """คำนวณระยะห่างระหว่างจุด 2 จุด"""
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def find_best_pairs_unified(self, detections_by_class):
        """หาคู่ที่ดีที่สุด - เฉพาะกรณีที่มีทั้งเลขห้องและมิเตอร์เท่านั้น"""
        room_detections = detections_by_class['roomN']
        meter_detections = detections_by_class['meter']
        decimal_detections = detections_by_class['meter1']
        
        # ใช้ logic เดิมในการหาคู่ที่ดีที่สุด
        if room_detections and meter_detections:
            best_pair = None
            best_score = -1
            
            for room in room_detections:
                for meter in meter_detections:
                    # คำนวณระยะห่างระหว่างเลขห้องและมิเตอร์
                    distance = self.calculate_distance(room['center'], meter['center'])
                    
                    # หาเลขทศนิยมที่ใกล้กับมิเตอร์นี้ที่สุด (ถ้ามี)
                    closest_decimal = None
                    min_decimal_distance = float('inf')
                    
                    for decimal in decimal_detections:
                        decimal_distance = self.calculate_distance(meter['center'], decimal['center'])
                        if decimal_distance < min_decimal_distance:
                            min_decimal_distance = decimal_distance
                            closest_decimal = decimal
                    
                    # แปลงระยะห่างเป็นคะแนน (ยิ่งใกล้ยิ่งได้คะแนนสูง)
                    distance_score = max(0, 1000 - distance) / 1000  # normalize ระยะห่าง
                    
                    # คะแนนจาก confidence
                    room_conf_score = room['confidence'] * 0.3 + room['detection_confidence'] * 0.2
                    meter_conf_score = meter['confidence'] * 0.3 + meter['detection_confidence'] * 0.2
                    
                    # คะแนนรวม
                    total_score = distance_score * 0.4 + room_conf_score + meter_conf_score
                    
                    # เพิ่มคะแนนถ้ามีเลขทศนิยมที่ใกล้
                    if closest_decimal and min_decimal_distance < 200:  # ถ้าเลขทศนิยมอยู่ใกล้ภายใน 200 pixels
                        decimal_bonus = closest_decimal['confidence'] * 0.1
                        total_score += decimal_bonus
                    
                    if total_score > best_score:
                        best_score = total_score
                        best_pair = {
                            'room': room,
                            'meter': meter,
                            'decimal': closest_decimal if closest_decimal and min_decimal_distance < 200 else None,
                            'distance': distance,
                            'score': total_score,
                            'pairing_method': 'proximity_matching'
                        }
            
            return best_pair
        
        return None

    def draw_detection_results_unified(self, img, best_pair, detections_by_class):
        """วาด bounding box และข้อความผลลัพธ์บนรูปภาพสำหรับคู่ที่ดีที่สุด"""
        display_img = img.copy()
        
        room_detections = detections_by_class['roomN']
        meter_detections = detections_by_class['meter']
        decimal_detections = detections_by_class['meter1']
        
        if best_pair:
            # วาดข้อมูลจากคู่ที่ดีที่สุด
            if best_pair['room']:
                room_data = best_pair['room']
                x1, y1, x2, y2 = room_data['box']
                cv2.rectangle(display_img, (x1, y1), (x2, y2), self.colors['roomN'], 2)
                cv2.putText(display_img, f"Room: {room_data['number']}", 
                           (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['roomN'], 2)
            
            if best_pair['meter']:
                meter_data = best_pair['meter']
                x1, y1, x2, y2 = meter_data['box']
                cv2.rectangle(display_img, (x1, y1), (x2, y2), self.colors['meter'], 2)
                cv2.putText(display_img, f"Meter: {meter_data['number']}", 
                           (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['meter'], 2)
            
            if best_pair['decimal']:
                decimal_data = best_pair['decimal']
                x1, y1, x2, y2 = decimal_data['box']
                cv2.rectangle(display_img, (x1, y1), (x2, y2), self.colors['meter1'], 2)
                cv2.putText(display_img, f"Decimal: {decimal_data['number']}", 
                           (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['meter1'], 2)
        else:
            # กรณีที่ไม่มีคู่ที่ดีที่สุด - วาดข้อมูลที่ดีที่สุดของแต่ละประเภท
            
            # วาดเลขห้องที่ดีที่สุด (ถ้ามี)
            if room_detections:
                best_room = max(room_detections, key=lambda x: x['confidence'] * 0.7 + x['detection_confidence'] * 0.3)
                x1, y1, x2, y2 = best_room['box']
                cv2.rectangle(display_img, (x1, y1), (x2, y2), self.colors['roomN'], 2)
                cv2.putText(display_img, f"Room: {best_room['number']}", 
                           (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['roomN'], 2)
            
            # วาดเลขมิเตอร์ที่ดีที่สุด (ถ้ามี)
            if meter_detections:
                best_meter = max(meter_detections, key=lambda x: x['confidence'] * 0.7 + x['detection_confidence'] * 0.3)
                x1, y1, x2, y2 = best_meter['box']
                cv2.rectangle(display_img, (x1, y1), (x2, y2), self.colors['meter'], 2)
                cv2.putText(display_img, f"Meter: {best_meter['number']}", 
                           (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['meter'], 2)
                
                # หาเลขทศนิยมที่ใกล้กับมิเตอร์นี้ที่สุด (ถ้ามี)
                closest_decimal = None
                min_decimal_distance = float('inf')
                
                for decimal in decimal_detections:
                    decimal_distance = self.calculate_distance(best_meter['center'], decimal['center'])
                    if decimal_distance < min_decimal_distance:
                        min_decimal_distance = decimal_distance
                        closest_decimal = decimal
                
                # วาดเลขทศนิยมที่ใกล้ที่สุด (ถ้าอยู่ใกล้พอ)
                if closest_decimal and min_decimal_distance < 600:
                    x1, y1, x2, y2 = closest_decimal['box']
                    cv2.rectangle(display_img, (x1, y1), (x2, y2), self.colors['meter1'], 2)
                    cv2.putText(display_img, f"Decimal: {closest_decimal['number']}", 
                               (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['meter1'], 2)
            
            # วาดเลขทศนิยมที่ดีที่สุด (ถ้าไม่มีมิเตอร์แต่มีทศนิยม)
            elif decimal_detections:
                best_decimal = max(decimal_detections, key=lambda x: x['confidence'] * 0.7 + x['detection_confidence'] * 0.3)
                x1, y1, x2, y2 = best_decimal['box']
                cv2.rectangle(display_img, (x1, y1), (x2, y2), self.colors['meter1'], 2)
                cv2.putText(display_img, f"Decimal: {best_decimal['number']}", 
                           (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['meter1'], 2)
        
        return display_img

    def process_image(self, image_path, output_folder):
        """
        ประมวลผลรูปภาพเพื่อค้นหาเลขห้องและเลขมิเตอร์โดยใช้ proximity matching
        ใหม่: ต้องเจอทั้งเลขห้องและเลขมิเตอร์ถึงจะบันทึกได้
        
        Args:
            image_path: เส้นทางของไฟล์รูปภาพ
            output_folder: โฟลเดอร์สำหรับบันทึกภาพที่ประมวลผลแล้ว

        Returns:
            dict: ผลลัพธ์การประมวลผล
        """
        # อ่านภาพ
        img = cv2.imread(image_path)
        if img is None:
            return {"error": "ไม่สามารถอ่านไฟล์รูปภาพได้"}
        
        # สร้าง dictionary เก็บผลลัพธ์
        results_dict = {
            'room_number': {"value": None, "confidence": 0, "method": None},
            'meter_number': {"value": None, "confidence": 0, "method": None},
            'decimal_number': {"value": None, "confidence": 0, "method": None},
            'full_meter': None,
            'google_drive_link': None,
            'image_path': image_path,
            'processed_image_path': None,
            'can_upload': False,
            'pairing_info': None
        }
        
        # เริ่มจับเวลา
        start_time = time.time()
        
        # ตรวจจับทุก bounding box และทำ OCR
        print("กำลังตรวจจับ...")
        detections_by_class = self.get_detections_by_class(img)
        
        room_detections = detections_by_class['roomN']
        meter_detections = detections_by_class['meter']
        decimal_detections = detections_by_class['meter1']
        
        print(f"พบเลขห้อง {len(room_detections)} ตัว, มิเตอร์ {len(meter_detections)} ตัว, ทศนิยม {len(decimal_detections)} ตัว")
        
        # หาคู่ที่ดีที่สุด
        best_pair = self.find_best_pairs_unified(detections_by_class)
        
        if best_pair:
            # เก็บผลลัพธ์เฉพาะกรณีที่มีทั้งเลขห้องและมิเตอร์
            results_dict['room_number'] = {
                "value": best_pair['room']['number'], 
                "confidence": float(best_pair['room']['confidence']), 
                "method": best_pair['room']['method']
            }
            
            results_dict['meter_number'] = {
                "value": best_pair['meter']['number'], 
                "confidence": float(best_pair['meter']['confidence']), 
                "method": best_pair['meter']['method']
            }
            
            # เลขทศนิยม (ถ้ามี)
            if best_pair['decimal']:
                results_dict['decimal_number'] = {
                    "value": best_pair['decimal']['number'], 
                    "confidence": float(best_pair['decimal']['confidence']), 
                    "method": best_pair['decimal']['method']
                }
                full_meter = f"{best_pair['meter']['number']}.{best_pair['decimal']['number']}"
            else:
                full_meter = best_pair['meter']['number']
            
            results_dict['full_meter'] = full_meter
            results_dict['can_upload'] = True
            
            # เก็บข้อมูลการจับคู่
            results_dict['pairing_info'] = {
                'distance': best_pair['distance'],
                'score': best_pair['score'],
                'pairing_method': best_pair['pairing_method'],
                'room_center': best_pair['room']['center'],
                'meter_center': best_pair['meter']['center'],
                'total_rooms_found': len(room_detections),
                'total_meters_found': len(meter_detections),
                'total_decimals_found': len(decimal_detections)
            }
            
            print(f"✅ เลือกคู่ที่ดีที่สุด: ห้อง {best_pair['room']['number']} - มิเตอร์ {best_pair['meter']['number']}")
            if best_pair['decimal']:
                print(f"   พร้อมทศนิยม: {best_pair['decimal']['number']}")
            print("✅ ข้อมูลครบถ้วน - สามารถบันทึกได้")
        
        else:
            # กรณีที่ไม่พบข้อมูลครบถ้วน
            print("❌ ไม่สามารถบันทึกได้ - ต้องเจอทั้งเลขห้องและเลขมิเตอร์")
            
            # เก็บข้อมูลที่พบแม้ไม่ครบถ้วน
            if room_detections:
                best_room = max(room_detections, key=lambda x: x['confidence'] * 0.7 + x['detection_confidence'] * 0.3)
                results_dict['room_number'] = {
                    "value": best_room['number'], 
                    "confidence": float(best_room['confidence']), 
                    "method": best_room['method']
                }
                print(f"   พบเลขห้อง: {best_room['number']} (confidence: {best_room['confidence']:.2f})")
            else:
                print("   ไม่พบเลขห้อง")
                
            if meter_detections:
                best_meter = max(meter_detections, key=lambda x: x['confidence'] * 0.7 + x['detection_confidence'] * 0.3)
                results_dict['meter_number'] = {
                    "value": best_meter['number'], 
                    "confidence": float(best_meter['confidence']), 
                    "method": best_meter['method']
                }
                
                # หาเลขทศนิยมที่ใกล้กับมิเตอร์นี้ที่สุด (ถ้ามี)
                closest_decimal = None
                min_decimal_distance = float('inf')
                
                for decimal in decimal_detections:
                    decimal_distance = self.calculate_distance(best_meter['center'], decimal['center'])
                    if decimal_distance < min_decimal_distance:
                        min_decimal_distance = decimal_distance
                        closest_decimal = decimal
                
                # เก็บข้อมูลทศนิยมถ้าอยู่ใกล้พอ
                if closest_decimal and min_decimal_distance < 600:
                    results_dict['decimal_number'] = {
                        "value": closest_decimal['number'], 
                        "confidence": float(closest_decimal['confidence']), 
                        "method": closest_decimal['method']
                    }
                    full_meter = f"{best_meter['number']}.{closest_decimal['number']}"
                    print(f"   พบเลขมิเตอร์: {best_meter['number']} พร้อมทศนิยม: {closest_decimal['number']}")
                else:
                    full_meter = best_meter['number']
                    print(f"   พบเลขมิเตอร์: {best_meter['number']} (confidence: {best_meter['confidence']:.2f})")
                
                results_dict['full_meter'] = full_meter
            else:
                print("   ไม่พบเลขมิเตอร์")
                
            # เก็บข้อมูลทศนิยมแม้ไม่มีมิเตอร์ (กรณีพิเศษ)
            if decimal_detections and not meter_detections:
                best_decimal = max(decimal_detections, key=lambda x: x['confidence'] * 0.7 + x['detection_confidence'] * 0.3)
                results_dict['decimal_number'] = {
                    "value": best_decimal['number'], 
                    "confidence": float(best_decimal['confidence']), 
                    "method": best_decimal['method']
                }
                print(f"   พบเลขทศนิยม: {best_decimal['number']} (confidence: {best_decimal['confidence']:.2f})")
            
            results_dict['pairing_info'] = {
                'total_rooms_found': len(room_detections),
                'total_meters_found': len(meter_detections),
                'total_decimals_found': len(decimal_detections),
                'pairing_method': 'insufficient_data',
                'error': 'ต้องเจอทั้งเลขห้องและเลขมิเตอร์จึงจะสามารถบันทึกได้'
            }
        
        # วาด bounding box บนรูปภาพ
        display_img = self.draw_detection_results_unified(img, best_pair, detections_by_class)
        
        # จบการจับเวลา
        end_time = time.time()
        elapsed_time = end_time - start_time
        results_dict['elapsed_time'] = elapsed_time
        
        # สร้างไฟล์ชื่อแบบสุ่มสำหรับบันทึกภาพ (ถ้าต้องการ)
        if output_folder:
            random_filename = f"{str(uuid.uuid4())}.jpg"
            output_path = os.path.join(output_folder, random_filename)
            cv2.imwrite(output_path, display_img)
            results_dict['processed_image'] = random_filename
            results_dict['processed_image_path'] = output_path
        
        return results_dict