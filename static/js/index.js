// index.js - JavaScript สำหรับหน้า index (ปรับปรุงแล้ว - มี Token Refresh)

document.addEventListener('DOMContentLoaded', function() {
    // ตัวแปร DOM elements
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    const uploadContent = uploadArea.querySelector('.upload-content');
    const imagePreviewWrapper = document.getElementById('imagePreviewWrapper');
    const imagePreview = document.getElementById('imagePreview');
    const removeImageBtn = document.getElementById('removeImageBtn');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const processButton = document.getElementById('processButton');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultContainer = document.getElementById('resultContainer');
    const saveContainer = document.getElementById('saveContainer');
    const saveToSheetsButton = document.getElementById('saveToSheetsButton');
    const savingIndicator = document.getElementById('savingIndicator');
    const saveResultMessage = document.getElementById('saveResultMessage');
    const saveSuccessMessage = document.getElementById('saveSuccessMessage');
    const saveErrorMessage = document.getElementById('saveErrorMessage');
    const googleDriveContainer = document.getElementById('googleDriveContainer');
    const googleDriveLink = document.getElementById('googleDriveLink');
    const uploadStatus = document.getElementById('uploadStatus');
    const saveTooltip = document.getElementById('saveTooltip');
    
    // สำหรับเก็บข้อมูลผลลัพธ์
    let resultData = null;

    // *** เพิ่ม: Token Refresh System ***
    let tokenRefreshInterval = null;
    
    function startTokenRefresh() {
        // ต่ออายุ token ทุก 45 นาที (3600 วินาที - 15 นาที buffer)
        tokenRefreshInterval = setInterval(async () => {
            try {
                console.log('🔄 Attempting to refresh token...');
                
                const response = await fetch('/api/refresh-token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    console.log('✅ Token refreshed successfully');
                } else {
                    console.warn('⚠️ Token refresh failed:', data.message);
                    
                    // ถ้า refresh ไม่สำเร็จ ให้แสดงข้อความแจ้งเตือน
                    if (data.redirect) {
                        showAuthWarning('การเข้าสู่ระบบหมดอายุ กรุณาเข้าสู่ระบบใหม่');
                    }
                }
            } catch (error) {
                console.error('❌ Error refreshing token:', error);
            }
        }, 45 * 60 * 1000); // 45 นาที
    }
    
    function stopTokenRefresh() {
        if (tokenRefreshInterval) {
            clearInterval(tokenRefreshInterval);
            tokenRefreshInterval = null;
        }
    }
    
    function showAuthWarning(message) {
        // สร้างหรือแสดง warning banner
        let warningBanner = document.getElementById('authWarningBanner');
        if (!warningBanner) {
            warningBanner = document.createElement('div');
            warningBanner.id = 'authWarningBanner';
            warningBanner.className = 'bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4';
            warningBanner.innerHTML = `
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                        </svg>
                    </div>
                    <div class="ml-3">
                        <p class="text-sm">${message}</p>
                        <p class="text-xs mt-1">
                            <a href="/logout" class="underline">คลิกที่นี่เพื่อเข้าสู่ระบบใหม่</a>
                        </p>
                    </div>
                    <div class="ml-auto pl-3">
                        <button onclick="this.parentElement.parentElement.parentElement.style.display='none'" class="text-yellow-700 hover:text-yellow-800">
                            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                            </svg>
                        </button>
                    </div>
                </div>
            `;
            
            // แทรกไว้ที่ด้านบนของ container
            const container = document.querySelector('.container');
            container.insertBefore(warningBanner, container.firstChild);
        }
        
        warningBanner.style.display = 'block';
    }
    
    function handleAuthError(errorData) {
        console.warn('🔒 Authentication error detected:', errorData);
        
        // หยุด token refresh
        stopTokenRefresh();
        
        // แสดงข้อความแจ้งเตือน
        showAuthWarning(errorData.error || 'การเข้าสู่ระบบหมดอายุ กรุณาเข้าสู่ระบบใหม่');
        
        // ปิดการใช้งานปุ่มที่ต้องใช้ authentication
        processButton.disabled = true;
        saveToSheetsButton.disabled = true;
        
        // เปลี่ยนข้อความปุ่ม
        processButton.textContent = 'กรุณาเข้าสู่ระบบใหม่';
        saveToSheetsButton.textContent = 'กรุณาเข้าสู่ระบบใหม่';
    }
    
    // เริ่ม token refresh เมื่อโหลดหน้า
    startTokenRefresh();
    
    // หยุด token refresh เมื่อปิดหน้า
    window.addEventListener('beforeunload', stopTokenRefresh);

    // ดึงข้อมูลผู้ใช้จาก Flask Session
    fetch('/get_user_info')
        .then(response => response.json())
        .then(data => {
            if (data.name) {
                document.getElementById('userName').textContent = data.name;
            }
            if (data.email) {
                document.getElementById('userEmail').textContent = data.email;
            }
            if (data.folder_link) {
                document.getElementById('googleFolderLink').href = data.folder_link;
            }
            if (data.photo_folder_link) {
                document.getElementById('googlePhotoFolderLink').href = data.photo_folder_link;
            }
            if (data.sheet_link) {
                document.getElementById('googleSheetLink').href = data.sheet_link;
            }
        })
        .catch(error => {
            console.error('Error fetching user info:', error);
        });

    // Upload area click event
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });

    // Drag & Drop events
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    // File input change event
    fileInput.addEventListener('change', function(e) {
        if (this.files && this.files[0]) {
            handleFileSelect(this.files[0]);
        }
    });

    // Remove image button
    removeImageBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        clearFileSelection();
    });

    // Handle file selection
    function handleFileSelect(file) {
        // Validate file type
        if (!file.type.startsWith('image/')) {
            alert('กรุณาเลือกไฟล์รูปภาพเท่านั้น');
            return;
        }

        // Validate file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('ขนาดไฟล์ต้องไม่เกิน 10MB');
            return;
        }

        // Update file input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;

        // Show file name
        fileNameDisplay.textContent = file.name;
        processButton.disabled = false;

        // Show image preview
        const reader = new FileReader();
        reader.onload = function(e) {
            imagePreview.src = e.target.result;
            uploadContent.classList.add('hide');
            imagePreviewWrapper.classList.remove('hide');
        }
        reader.readAsDataURL(file);

        // Hide old results
        resultContainer.classList.add('hide');
        saveContainer.classList.add('hide');

        // Reset save button and messages
        resetSaveUI();
    }

    // Clear file selection
    function clearFileSelection() {
        fileInput.value = '';
        fileNameDisplay.textContent = 'ยังไม่ได้เลือกไฟล์';
        processButton.disabled = true;
        uploadContent.classList.remove('hide');
        imagePreviewWrapper.classList.add('hide');
        imagePreview.src = '';
    }

    // Reset save UI
    function resetSaveUI() {
        saveToSheetsButton.disabled = false;
        savingIndicator.style.display = 'none';
        saveResultMessage.classList.add('hide');
        saveSuccessMessage.classList.add('hide');
        saveErrorMessage.classList.add('hide');
    }
    
    // ประมวลผล (ปรับปรุงแล้ว - มี Auth Error Handling)
    processButton.addEventListener('click', function() {
        if (fileInput.files && fileInput.files[0]) {
            // แสดงการโหลด
            loadingIndicator.style.display = 'block';
            processButton.disabled = true;
            resultContainer.classList.add('hide');
            saveContainer.classList.add('hide');

            // Reset save button and messages before new processing
            resetSaveUI();
            
            // สร้าง FormData
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            // ส่ง request ไปยัง API
            fetch('/process', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // ซ่อนการโหลด
                loadingIndicator.style.display = 'none';
                processButton.disabled = false;
                
                // ตรวจสอบ auth error
                if (data.auth_error) {
                    handleAuthError(data);
                    return;
                }
                
                if (data.error) {
                    alert('เกิดข้อผิดพลาด: ' + data.error);
                    return;
                }
                
                // เก็บข้อมูลผลลัพธ์สำหรับการบันทึก
                resultData = data;
                
                // แสดงผลลัพธ์
                displayResults(data);

                // *** ตรวจสอบเงื่อนไขใหม่: ต้องมีทั้งเลขห้องและเลขมิเตอร์ ***
                if (data.can_upload && data.room_number && data.room_number.value && 
                    data.meter_number && data.meter_number.value) {
                    saveContainer.classList.remove('hide');
                    updateSaveTooltip(data);
                    saveToSheetsButton.disabled = false;
                } else {
                    // แสดงข้อความแจ้งเหตุผลที่ไม่สามารถบันทึกได้
                    showCannotSaveReason(data);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                loadingIndicator.style.display = 'none';
                processButton.disabled = false;
                alert('เกิดข้อผิดพลาดในการเชื่อมต่อ: ' + error);
            });
        }
    });

    // บันทึกลง Google Sheets (ปรับปรุงแล้ว - มี Auth Error Handling)
    saveToSheetsButton.addEventListener('click', function() {
        if (!resultData || !resultData.can_upload) {
            alert('ไม่มีข้อมูลที่จะบันทึก หรือข้อมูลไม่ครบถ้วน (ต้องมีทั้งเลขห้องและเลขมิเตอร์)');
            return;
        }

        // ตรวจสอบอีกครั้งว่ามีข้อมูลครบ
        const roomNumberInput = document.getElementById('roomNumberInput');
        const meterNumberInput = document.getElementById('meterNumberInput');
        
        if (!roomNumberInput.value.trim() || !meterNumberInput.value.trim()) {
            alert('กรุณากรอกเลขห้องและเลขมิเตอร์ให้ครบถ้วน');
            return;
        }

        // แสดงการโหลด
        savingIndicator.style.display = 'block';
        saveToSheetsButton.disabled = true;
        saveResultMessage.classList.add('hide');
        saveSuccessMessage.classList.add('hide');
        saveErrorMessage.classList.add('hide');

        // เตรียมข้อมูลสำหรับบันทึก
        const decimalNumberInput = document.getElementById('decimalNumberInput');

        const dataToBeSaved = {
            room_number: roomNumberInput.value.trim(),
            room_edited: roomNumberInput.dataset.edited === 'true',
            meter_number: meterNumberInput.value.trim(),
            meter_edited: meterNumberInput.dataset.edited === 'true',
            decimal_number: decimalNumberInput.value.trim(),
            decimal_edited: decimalNumberInput.dataset.edited === 'true',
            full_meter: document.getElementById('fullMeterDisplay').textContent,
            google_drive_link: resultData.google_drive_link,
            processed_image_path: resultData.processed_image_path
        };

        // ส่ง request ไปยัง API
        fetch('/save-to-sheets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(dataToBeSaved)
        })
        .then(response => response.json())
        .then(data => {
            // ซ่อนการโหลด
            savingIndicator.style.display = 'none';
            saveToSheetsButton.disabled = false;
            saveResultMessage.classList.remove('hide');

            // ตรวจสอบ auth error
            if (data.auth_error) {
                handleAuthError(data);
                return;
            }

            if (data.error) {
                saveErrorMessage.textContent = data.error;
                saveErrorMessage.classList.remove('hide');
            } else {
                saveSuccessMessage.classList.remove('hide');
                // ปิดปุ่มบันทึกหลังจากบันทึกสำเร็จ
                saveToSheetsButton.disabled = true;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            savingIndicator.style.display = 'none';
            saveToSheetsButton.disabled = false;
            saveResultMessage.classList.remove('hide');
            saveErrorMessage.textContent = 'เกิดข้อผิดพลาดในการเชื่อมต่อ';
            saveErrorMessage.classList.remove('hide');
        });
    });

    // แสดงเหตุผลที่ไม่สามารถบันทึกได้
    function showCannotSaveReason(data) {
        // สร้าง element แสดงข้อความแจ้งเหตุผล
        let reasonContainer = document.getElementById('cannotSaveReason');
        if (!reasonContainer) {
            reasonContainer = document.createElement('div');
            reasonContainer.id = 'cannotSaveReason';
            reasonContainer.className = 'bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mt-4';
            
            // แทรกหลังจาก resultContainer แทนที่จะใช้ saveContainer
            resultContainer.insertAdjacentElement('afterend', reasonContainer);
        }

        let reasonText = '⚠️ ไม่สามารถบันทึกข้อมูลได้เนื่องจาก: ';
        let reasons = [];

        if (!data.room_number || !data.room_number.value) {
            reasons.push('ไม่พบเลขห้อง');
        }

        if (!data.meter_number || !data.meter_number.value) {
            reasons.push('ไม่พบเลขมิเตอร์');
        }

        if (reasons.length === 0) {
            reasons.push('ข้อมูลไม่ครบถ้วนหรือไม่สามารถจับคู่ข้อมูลได้');
        }

        reasonText += reasons.join(' และ ');
        reasonText += '<br><small class="text-yellow-600">หมายเหตุ: ระบบต้องตรวจพบทั้งเลขห้องและเลขมิเตอร์จึงจะสามารถบันทึกข้อมูลได้</small>';

        reasonContainer.innerHTML = reasonText;
        reasonContainer.classList.remove('hide');
    }
    
    // แสดงผลลัพธ์
    function displayResults(data) {
        // แสดง container ผลลัพธ์
        resultContainer.classList.remove('hide');
        
        // ซ่อนข้อความแจ้งเหตุผลเก่า (ถ้ามี)
        const reasonContainer = document.getElementById('cannotSaveReason');
        if (reasonContainer) {
            reasonContainer.classList.add('hide');
        }
        
        // เลขห้อง - แสดงแม้ว่าจะไม่สามารถบันทึกได้
        const roomNumberInput = document.getElementById('roomNumberInput');
        const roomConfidenceElem = document.getElementById('roomConfidence');
        if (data.room_number && data.room_number.value !== null) {
            roomNumberInput.value = data.room_number.value;
            roomNumberInput.dataset.originalValue = data.room_number.value;
            roomConfidenceElem.textContent = `ความเชื่อมั่น: ${(data.room_number.confidence * 100).toFixed(1)}%`;
            // เปลี่ยนสีตัวอักษรเป็นเขียวเมื่อพบข้อมูล
            roomNumberInput.style.color = '#059669';
        } else {
            roomNumberInput.value = '';
            roomNumberInput.dataset.originalValue = '';
            roomConfidenceElem.textContent = 'ไม่พบข้อมูล';
            // เปลี่ยนสีตัวอักษรเป็นแดงเมื่อไม่พบข้อมูล
            roomNumberInput.style.color = '#dc2626';
        }
        roomNumberInput.dataset.edited = 'false';

        // เลขมิเตอร์ - แสดงแม้ว่าจะไม่สามารถบันทึกได้
        const fullMeterDisplayElem = document.getElementById('fullMeterDisplay');
        const meterNumberInput = document.getElementById('meterNumberInput');
        const meterConfidenceElem = document.getElementById('meterConfidence');
        const decimalNumberInput = document.getElementById('decimalNumberInput');
        const decimalConfidenceElem = document.getElementById('decimalConfidence');

        // แสดงข้อมูลมิเตอร์เต็ม
        if (data.full_meter !== null) {
            fullMeterDisplayElem.textContent = data.full_meter;
            fullMeterDisplayElem.style.color = '#059669';
        } else {
            fullMeterDisplayElem.textContent = 'ไม่พบข้อมูลครบถ้วน';
            fullMeterDisplayElem.style.color = '#dc2626';
        }

        // แสดงข้อมูลเลขมิเตอร์หลัก
        if (data.meter_number && data.meter_number.value !== null) {
            meterNumberInput.value = data.meter_number.value;
            meterNumberInput.dataset.originalValue = data.meter_number.value;
            meterConfidenceElem.textContent = `ความเชื่อมั่น: ${(data.meter_number.confidence * 100).toFixed(1)}%`;
            meterNumberInput.style.color = '#059669';
        } else {
            meterNumberInput.value = '';
            meterNumberInput.dataset.originalValue = '';
            meterConfidenceElem.textContent = 'ไม่พบข้อมูล';
            meterNumberInput.style.color = '#dc2626';
        }
        meterNumberInput.dataset.edited = 'false';

        // แสดงข้อมูลเลขทศนิยม
        if (data.decimal_number && data.decimal_number.value !== null) {
            decimalNumberInput.value = data.decimal_number.value;
            decimalNumberInput.dataset.originalValue = data.decimal_number.value;
            decimalConfidenceElem.textContent = `ความเชื่อมั่น: ${(data.decimal_number.confidence * 100).toFixed(1)}%`;
            decimalNumberInput.style.color = '#059669';
        } else {
            decimalNumberInput.value = '';
            decimalNumberInput.dataset.originalValue = '';
            decimalConfidenceElem.textContent = 'ไม่พบข้อมูล';
            decimalNumberInput.style.color = '#6b7280';
        }
        decimalNumberInput.dataset.edited = 'false';

        // Update full meter display when meter or decimal inputs change
        const updateFullMeterDisplay = () => {
            const meterValue = meterNumberInput.value.trim();
            const decimalValue = decimalNumberInput.value.trim();
            if (meterValue && decimalValue) {
                fullMeterDisplayElem.textContent = `${meterValue}.${decimalValue}`;
                fullMeterDisplayElem.style.color = '#059669';
            } else if (meterValue) {
                fullMeterDisplayElem.textContent = meterValue;
                fullMeterDisplayElem.style.color = '#059669';
            } else {
                fullMeterDisplayElem.textContent = 'ไม่พบข้อมูลครบถ้วน';
                fullMeterDisplayElem.style.color = '#dc2626';
            }
        };

        meterNumberInput.addEventListener('input', updateFullMeterDisplay);
        decimalNumberInput.addEventListener('input', updateFullMeterDisplay);

        // Add event listeners to track edits
        document.querySelectorAll('.editable-number').forEach(input => {
            input.addEventListener('input', function() {
                if (this.value !== this.dataset.originalValue) {
                    this.dataset.edited = 'true';
                } else {
                    this.dataset.edited = 'false';
                }
            });
        });
        
        // เวลาที่ใช้
        document.getElementById('elapsedTime').textContent = `${data.elapsed_time.toFixed(2)} วินาที`;
        
        // ภาพที่ประมวลผลแล้ว
        if (data.processed_image) {
            document.getElementById('processedImage').src = `/processed/${data.processed_image}`;
        }

        // แสดงสถานะการอัปโหลดไปยัง Google Drive
        if (data.google_drive_link) {
            googleDriveContainer.classList.remove('hide');
            googleDriveLink.href = data.google_drive_link;
            uploadStatus.textContent = 'อัปโหลดสำเร็จ';
            uploadStatus.className = 'badge badge-success mr-2 mb-1 sm:mb-0';
            googleDriveLink.classList.remove('hide');
        } else if (data.can_upload) {
            googleDriveContainer.classList.remove('hide');
            googleDriveLink.href = '#';
            uploadStatus.textContent = 'ไม่สามารถอัปโหลดได้';
            uploadStatus.className = 'badge badge-error mr-2 mb-1 sm:mb-0';
            googleDriveLink.classList.add('hide');
        } else {
            // *** กรณีที่ข้อมูลไม่ครับ - แสดงสถานะที่ชัดเจน ***
            googleDriveContainer.classList.remove('hide');
            googleDriveLink.href = '#';
            uploadStatus.textContent = 'ข้อมูลไม่ครบ - ไม่อัปโหลด';
            uploadStatus.className = 'badge badge-warning mr-2 mb-1 sm:mb-0';
            googleDriveLink.classList.add('hide');
        }
        
        // เลื่อนไปยัง container ผลลัพธ์
        setTimeout(() => {
            resultContainer.scrollIntoView({ behavior: 'smooth' });
        }, 100);
    }

    // อัพเดทข้อความใน tooltip สำหรับแสดงข้อมูลที่จะบันทึก
    function updateSaveTooltip(data) {
        let tooltipText = '';
        
        if (data.room_number && data.room_number.value) {
            tooltipText += `เลขห้อง: ${data.room_number.value}, `;
        } else {
            tooltipText += 'เลขห้อง: ไม่พบข้อมูล, ';
        }
        
        if (data.full_meter) {
            tooltipText += `เลขมิเตอร์: ${data.full_meter}, `;
        } else {
            tooltipText += 'เลขมิเตอร์: ไม่พบข้อมูลครบถ้วน, ';
        }
        
        tooltipText += 'วันเวลา: ปัจจุบัน';
        
        if (data.google_drive_link) {
            tooltipText += ', พร้อมลิงก์รูปภาพ';
        } else {
            tooltipText += ', ไม่มีลิงก์รูปภาพ';
        }
        
        saveTooltip.textContent = tooltipText;
    }

    // เพิ่มสไตล์ CSS สำหรับ badge-warning ถ้ายังไม่มี
    if (!document.querySelector('style[data-badge-warning]')) {
        const style = document.createElement('style');
        style.setAttribute('data-badge-warning', 'true');
        style.textContent = `
            .badge-warning {
                background-color: #f59e0b;
                color: white;
            }
        `;
        document.head.appendChild(style);
    }

    // *** เพิ่ม: Manual Token Refresh Button (สำหรับ debugging) ***
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        const debugPanel = document.createElement('div');
        debugPanel.style.cssText = 'position: fixed; top: 10px; right: 10px; background: #f0f0f0; padding: 10px; border-radius: 5px; z-index: 9999; font-size: 12px;';
        debugPanel.innerHTML = `
            <strong>Debug Panel</strong><br>
            <button id="manualRefreshBtn" style="margin-top: 5px; padding: 5px 10px; background: #3b82f6; color: white; border: none; border-radius: 3px; cursor: pointer;">
                Manual Token Refresh
            </button>
            <div id="tokenStatus" style="margin-top: 5px; font-size: 11px;">
                Token Status: Unknown
            </div>
        `;
        document.body.appendChild(debugPanel);
        
        document.getElementById('manualRefreshBtn').addEventListener('click', async () => {
            const statusDiv = document.getElementById('tokenStatus');
            statusDiv.textContent = 'Refreshing...';
            
            try {
                const response = await fetch('/api/refresh-token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    statusDiv.textContent = 'Token Status: ✅ Refreshed';
                    statusDiv.style.color = 'green';
                } else {
                    statusDiv.textContent = 'Token Status: ❌ Failed';
                    statusDiv.style.color = 'red';
                }
            } catch (error) {
                statusDiv.textContent = 'Token Status: ❌ Error';
                statusDiv.style.color = 'red';
            }
        });
    }
});