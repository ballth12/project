// login.js - JavaScript สำหรับหน้า login

document.addEventListener('DOMContentLoaded', function() {
    // ฟังก์ชันสำหรับการเปลี่ยนแปลงบนหน้า login
    // (ยังไม่มีฟังก์ชันพิเศษแต่สามารถเพิ่มได้ในอนาคต)
    
    // เพิ่ม event listener สำหรับปุ่ม login ถ้าต้องการ
    const loginButton = document.querySelector('.google-btn');
    if (loginButton) {
        loginButton.addEventListener('click', function() {
            // สามารถเพิ่มพฤติกรรมเพิ่มเติมได้ที่นี่ เช่น แสดงการโหลด
            // หรือปิดใช้งานปุ่มระหว่างการเข้าสู่ระบบ
        });
    }
});