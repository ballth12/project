# test_detector.py
import os
import cv2
import time
from detector import ImageDetector
import glob
from pathlib import Path

def test_detector_batch(test_folder_path, output_folder):
    """
    ทดสอบ detector กับรูปทั้งหมดใน folder และบันทึกผลลัพธ์แยกตามประเภท
    
    Args:
        test_folder_path: เส้นทางของ folder ที่มีรูปทดสอบ
        output_folder: folder สำหรับเก็บผลลัพธ์
    """
    
    # สร้าง detector
    print("กำลังโหลด detector...")
    detector = ImageDetector({
        'model_path': 'bestMR.pt',
        'use_gpu': True
    })
    
    # สร้าง output folder ถ้ายังไม่มี
    os.makedirs(output_folder, exist_ok=True)
    
    # เตรียมไฟล์ผลลัพธ์
    roomN_file = os.path.join(output_folder, 'roomN.txt')
    meter_file = os.path.join(output_folder, 'meter.txt')
    meter1_file = os.path.join(output_folder, 'meter1.txt')
    summary_file = os.path.join(output_folder, 'summary.txt')
    
    # ล้างไฟล์เก่า
    for file_path in [roomN_file, meter_file, meter1_file, summary_file]:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # ค้นหาไฟล์รูปทั้งหมด
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(test_folder_path, ext)))
        image_files.extend(glob.glob(os.path.join(test_folder_path, ext.upper())))
    
    # กำจัดไฟล์ซ้ำด้วย set() แล้วแปลงกลับเป็น list
    image_files = list(set(image_files))
    
    # เรียงลำดับไฟล์ตามชื่อแบบ natural sort (m1, m2, m3, ..., m10, m11)
    import re
    def natural_sort_key(filename):
        """สร้าง key สำหรับเรียงลำดับแบบ natural"""
        basename = os.path.basename(filename)
        # แยกตัวเลขออกมาจากชื่อไฟล์
        parts = re.split(r'(\d+)', basename)
        # แปลงส่วนที่เป็นตัวเลขให้เป็น int เพื่อเรียงลำดับถูกต้อง
        return [int(part) if part.isdigit() else part for part in parts]
    
    image_files.sort(key=natural_sort_key)  # เรียงลำดับไฟล์แบบ natural
    
    if not image_files:
        print(f"ไม่พบไฟล์รูปใน folder: {test_folder_path}")
        return
    
    print(f"พบไฟล์รูป {len(image_files)} ไฟล์")
    print("เริ่มการทดสอบ...")
    print("-" * 60)
    
    # สถิติ
    total_files = len(image_files)
    processed_files = 0
    error_files = 0
    total_time = 0
    
    # เก็บผลลัพธ์ทั้งหมด
    all_roomN_results = []
    all_meter_results = []
    all_meter1_results = []
    summary_results = []
    
    # ประมวลผลทีละไฟล์ (Real-time)
    for i, image_path in enumerate(image_files, 1):
        filename = os.path.basename(image_path)
        print(f"\n[{i}/{total_files}] ประมวลผล: {filename}")
        
        try:
            start_time = time.time()
            
            # อ่านภาพ
            img = cv2.imread(image_path)
            if img is None:
                print(f"  ❌ ไม่สามารถอ่านไฟล์ได้: {filename}")
                error_files += 1
                continue
            
            # ตรวจจับทุก bounding box และแยกตาม class
            detections_by_class = detector.get_detections_by_class(img)
            
            room_detections = detections_by_class['roomN']
            meter_detections = detections_by_class['meter']
            decimal_detections = detections_by_class['meter1']
            
            # หาคู่ที่ดีที่สุด (สำหรับ summary)
            best_pair = detector.find_best_pairs_unified(detections_by_class)
            
            end_time = time.time()
            process_time = end_time - start_time
            total_time += process_time
            
            print(f"  📊 พบ: ห้อง {len(room_detections)}, มิเตอร์ {len(meter_detections)}, ทศนิยม {len(decimal_detections)}")
            print(f"  ⏱️  เวลา: {process_time:.2f} วินาที")
            
            # เก็บและแสดงผลลัพธ์ roomN แบบ real-time
            if room_detections:
                for j, detection in enumerate(room_detections):
                    # สร้างชื่อไฟล์ในรูปแบบ m1_1.jpg, m1_2.jpg ถ้าเจอหลายตัว
                    if len(room_detections) > 1:
                        display_name = f"{os.path.splitext(filename)[0]}_{j+1}{os.path.splitext(filename)[1]}"
                    else:
                        display_name = f"{os.path.splitext(filename)[0]}_1{os.path.splitext(filename)[1]}"
                    
                    result_line = f"{display_name} = {detection['number']}"
                    all_roomN_results.append(result_line)
                    # บันทึกทันทีลงไฟล์
                    with open(roomN_file, 'a', encoding='utf-8') as f:
                        f.write(result_line + '\n')
                print(f"  🏠 เลขห้อง: {[d['number'] for d in room_detections]}")
            
            # เก็บและแสดงผลลัพธ์ meter แบบ real-time
            if meter_detections:
                for j, detection in enumerate(meter_detections):
                    # สร้างชื่อไฟล์ในรูปแบบ m1_1.jpg, m1_2.jpg ถ้าเจอหลายตัว
                    if len(meter_detections) > 1:
                        display_name = f"{os.path.splitext(filename)[0]}_{j+1}{os.path.splitext(filename)[1]}"
                    else:
                        display_name = f"{os.path.splitext(filename)[0]}_1{os.path.splitext(filename)[1]}"
                    
                    result_line = f"{display_name} = {detection['number']}"
                    all_meter_results.append(result_line)
                    # บันทึกทันทีลงไฟล์
                    with open(meter_file, 'a', encoding='utf-8') as f:
                        f.write(result_line + '\n')
                print(f"  🔢 เลขมิเตอร์: {[d['number'] for d in meter_detections]}")
            
            # เก็บและแสดงผลลัพธ์ meter1 แบบ real-time
            if decimal_detections:
                for j, detection in enumerate(decimal_detections):
                    # สร้างชื่อไฟล์ในรูปแบบ m1_1.jpg, m1_2.jpg ถ้าเจอหลายตัว
                    if len(decimal_detections) > 1:
                        display_name = f"{os.path.splitext(filename)[0]}_{j+1}{os.path.splitext(filename)[1]}"
                    else:
                        display_name = f"{os.path.splitext(filename)[0]}_1{os.path.splitext(filename)[1]}"
                    
                    result_line = f"{display_name} = {detection['number']}"
                    all_meter1_results.append(result_line)
                    # บันทึกทันทีลงไฟล์
                    with open(meter1_file, 'a', encoding='utf-8') as f:
                        f.write(result_line + '\n')
                print(f"  🔸 เลขทศนิยม: {[d['number'] for d in decimal_detections]}")
            
            # เก็บและแสดงข้อมูล summary แบบ real-time
            if best_pair:
                summary_line = f"{filename} = Room: {best_pair['room']['number']}, Meter: {best_pair['meter']['number']}"
                if best_pair['decimal']:
                    summary_line += f", Decimal: {best_pair['decimal']['number']}"
                    summary_line += f", Full: {best_pair['meter']['number']}.{best_pair['decimal']['number']}"
                else:
                    summary_line += f", Full: {best_pair['meter']['number']}"
                summary_line += f" (score: {best_pair['score']:.3f}, distance: {best_pair['distance']:.1f})"
                summary_results.append(summary_line)
                # บันทึกทันทีลงไฟล์ summary
                with open(summary_file, 'a', encoding='utf-8') as f:
                    f.write(summary_line + '\n')
                print(f"  ✅ คู่ที่ดีที่สุด: ห้อง {best_pair['room']['number']}, มิเตอร์ {best_pair['meter']['number']}")
            else:
                summary_line = f"{filename} = ไม่พบคู่ที่สมบูรณ์"
                summary_results.append(summary_line)
                # บันทึกทันทีลงไฟล์ summary
                with open(summary_file, 'a', encoding='utf-8') as f:
                    f.write(summary_line + '\n')
                print(f"  ❌ ไม่พบคู่ที่สมบูรณ์")
            
            processed_files += 1
            
            # แสดงสถิติแบบ real-time
            avg_time = total_time / processed_files
            remaining_files = total_files - i
            estimated_time = remaining_files * avg_time
            print(f"  📈 ความคืบหน้า: {processed_files}/{total_files} ({(processed_files/total_files)*100:.1f}%)")
            print(f"  ⏰ เวลาเฉลี่ย: {avg_time:.2f}s, คาดเหลือ: {estimated_time:.1f}s")
            
        except Exception as e:
            print(f"  ❌ เกิดข้อผิดพลาด: {str(e)}")
            error_files += 1
    
    # บันทึกผลลัพธ์ลงไฟล์
    print("\nกำลังเตรียมไฟล์ผลลัพธ์...")
    
    # แสดงสรุปผลสุดท้าย
    print("\n" + "=" * 60)
    print("🎉 การทดสอบเสร็จสิ้น!")
    print("=" * 60)
    print(f"📁 จำนวนไฟล์ทั้งหมด: {total_files}")
    print(f"✅ ประมวลผลสำเร็จ: {processed_files}")
    print(f"❌ ข้อผิดพลาด: {error_files}")
    print(f"⏱️  เวลารวม: {total_time:.2f} วินาที")
    print(f"📊 เวลาเฉลี่ยต่อรูป: {total_time/max(processed_files, 1):.2f} วินาที")
    print()
    print(f"📄 ผลลัพธ์เลขห้อง: {len(all_roomN_results)} รายการ")
    print(f"📄 ผลลัพธ์เลขมิเตอร์: {len(all_meter_results)} รายการ")
    print(f"📄 ผลลัพธ์เลขทศนิยม: {len(all_meter1_results)} รายการ")
    print()
    print(f"💾 ไฟล์ผลลัพธ์บันทึกไว้ใน folder: {output_folder}")
    print(f"   - {roomN_file}")
    print(f"   - {meter_file}")
    print(f"   - {meter1_file}")
    print(f"   - {summary_file}")

def main():
    """
    ฟังก์ชันหลักสำหรับเรียกใช้งาน
    """
    test_folder = "data-test"
    output_folder="metertest4"
    
    # ตรวจสอบว่า folder มีอยู่จริงหรือไม่
    if not os.path.exists(test_folder):
        print(f"❌ ไม่พบ folder: {test_folder}")
        print("กรุณาสร้าง folder และใส่รูปทดสอบลงไป")
        return
    
    print(f"📁 เริ่มทดสอบกับ folder: {test_folder}")
    print()
    
    # เริ่มการทดสอบ
    test_detector_batch(test_folder,output_folder)

if __name__ == "__main__":
    main()