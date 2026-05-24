# RoomMeterApp 🏠⚡

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)
[![YOLOv11](https://img.shields.io/badge/YOLO-v11-orange.svg)](https://ultralytics.com/)

An AI-powered web application designed to automate the reading and recording of utility meters. By using computer vision, it detects room numbers and meter values (both integer and decimal) from uploaded photos and syncs the data directly to Google Sheets.

## 🌟 Key Features

- **AI Object Detection:** Uses a custom-trained YOLO model to identify room numbers and meter displays.
- **Intelligent OCR:** Employs EasyOCR with advanced image preprocessing (CLAHE, Otsu thresholding) for high-accuracy digit recognition.
- **Proximity Matching:** Automatically pairs room numbers with their corresponding meters based on spatial analysis within the image.
- **Google Cloud Integration:**
  - **Google Drive:** Automatically saves processed images with detection overlays.
  - **Google Sheets:** Logs data (timestamp, room, meter reading) in real-time.
- **Secure Authentication:** Implements Google OAuth2 with PKCE for secure access to user cloud storage.
- **Responsive UI:** Modern, mobile-friendly interface with Dark/Light mode support.

## 🛠️ Tech Stack

- **Backend:** Python (Flask)
- **Computer Vision:** Ultralytics (YOLOv11), EasyOCR, OpenCV
- **Integration:** Google Drive API v3, Google Sheets API v4
- **Frontend:** Vanilla JavaScript, Tailwind CSS

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher.
- A Google Cloud Project with **Google Drive API** and **Google Sheets API** enabled.
- OAuth2 credentials (Client ID and Client Secret).

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ballth12/project.git
   cd project
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\activate

   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your_flask_secret_key
   GOOGLE_CLIENT_SECRET='{"web":{"client_id":"...","client_secret":"..."}}'
   REDIRECT_URI=http://localhost:8080/callback
   ```

### Running the App

```bash
python app.py
```
Open your browser and navigate to `http://localhost:8080`.

## 📖 Usage

1. **Login:** Sign in with your Google account to grant permission for Drive and Sheets access.
2. **Setup:** The app will automatically create a `RoomMeterApp` folder in your Google Drive and a `RoomMeterData` spreadsheet.
3. **Upload:** Upload a clear photo containing both a room number and a meter.
4. **Verify:** Review the AI detections. You can manually edit the values if necessary.
5. **Save:** Click "บันทึกข้อมูล" (Save) to append the reading to your Google Sheet and upload the processed image to Drive.

## 🛡️ License

This project is for educational/internal use. See the repository owner for licensing details.

---
*Developed with ❤️ using Gemini CLI and Python.*
