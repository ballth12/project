// theme.js - ฟังก์ชันสำหรับการเปลี่ยน theme (Dark/Light mode)

document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    
    // ฟังก์ชันสำหรับการตั้งค่า theme
    function setTheme(isDark) {
        if (isDark) {
            html.classList.add('dark');
            themeToggle.checked = true;
        } else {
            html.classList.remove('dark');
            themeToggle.checked = false;
        }
        // บันทึกการตั้งค่าลงใน localStorage
        localStorage.setItem('darkMode', isDark ? 'enabled' : 'disabled');
    }
    
    // โหลดค่า theme ที่บันทึกไว้
    const savedTheme = localStorage.getItem('darkMode');
    if (savedTheme === 'enabled') {
        setTheme(true);
    } else if (savedTheme === 'disabled') {
        setTheme(false);
    } else {
        // ถ้าไม่มีการบันทึกค่า ให้ตรวจสอบการตั้งค่าของระบบ
        const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
        setTheme(prefersDarkScheme.matches);
        
        // ติดตามการเปลี่ยนแปลงการตั้งค่าของระบบ
        prefersDarkScheme.addEventListener('change', (e) => {
            if (localStorage.getItem('darkMode') === null) {
                setTheme(e.matches);
            }
        });
    }
    
    // สลับ theme เมื่อคลิกที่สวิตช์
    if (themeToggle) {
        themeToggle.addEventListener('change', function() {
            setTheme(this.checked);
        });
    }
});