# Onboarding & Development Guide for AI Agents (AGENTS.md) 🤖⚡

Welcome to **RoomMeterApp**! This document provides information on the project's architecture, setup, guidelines, and commands to help AI agents and developers onboard and work effectively with this codebase.

---

## 📌 Project Overview
**RoomMeterApp** is an AI-powered utility meter reading application. It allows users to upload images of water/electricity meters along with their room numbers. A custom YOLO model detects regions of interest (room number, integer meter display, and decimal meter display), preprocesses these regions, runs OCR to read the text, pairs the room with the closest meter using proximity algorithms, and logs the verified values into Google Sheets while archiving the processed image in Google Drive.

---

## 🛠️ Environment Setup & Installation

### Prerequisites
- **Python:** 3.10 or higher
- **GPU (Optional but recommended):** CUDA-compatible device for accelerating YOLO and EasyOCR inferences.

### Installation Steps

1. **Set up Virtual Environment:**
   ```bash
   # Create a virtual environment
   python -m venv .venv

   # Activate the environment (Windows)
   .\.venv\Scripts\activate

   # Activate the environment (Linux/macOS)
   source .venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *Note:* The main requirements include `flask`, `ultralytics` (YOLO), `easyocr`, `opencv-python`, and Google Client Libraries.

3. **Configure Environment Variables (`.env`):**
   Create a `.env` file at the root of the project with the following:
   ```env
   SECRET_KEY=your_flask_secret_key
   GOOGLE_CLIENT_SECRET='{"web":{"client_id":"...","client_secret":"..."}}'
   REDIRECT_URI=http://localhost:8080/callback
   ```
   *Note:* You must configure a Google Cloud Console project with the Google Drive API and Google Sheets API enabled, and download the OAuth 2.0 Web Client credentials.

---

## 🚀 Running the Application

### Development Server
Run the local Flask development server (auto-reloads on file changes):
```bash
python app.py
```
Open a browser and navigate to `http://localhost:8080`.

### Production Server
Run the Waitress WSGI production server:
```bash
python server.py
```
*Note:* The production server listens on `0.0.0.0` at the port defined in the `PORT` environment variable (defaults to `8080`).

---

## 🧪 Verification & Testing Commands

Currently, there is no formal test suite (e.g. Pytest) in the project, but there is a validation set under `ground_truth/`.

### Standalone Inference Testing (Sanity Check)
To verify that the YOLO model loading and OpenCV/EasyOCR pipeline function correctly, you can run a quick standalone python script:

```python
# Save this in C:/Users/ballt/Desktop/project/meter/scratch/test_detector.py and run it
import os
from detector import ImageDetector

# Initialize the detector
detector = ImageDetector({
    'model_path': 'bestMR.pt',
    'use_gpu': False # Set to True if CUDA is configured
})

# Process a test image
test_image = "uploads/some_test_image.jpg"
if os.path.exists(test_image):
    result = detector.process_image(test_image, output_folder="processed")
    print("Inference results:", result)
else:
    print(f"Please place an image at {test_image} to run this test.")
```

Run the script:
```bash
python scratch/test_detector.py
```

---

## 📂 Key Codebase Components

- **[app.py](file:///C:/Users/ballt/Desktop/project/meter/app.py):** Main Flask application containing routes for the web interface, OAuth authentication flow (`/auth`, `/callback`), image uploading, and database records saving.
- **[detector.py](file:///C:/Users/ballt/Desktop/project/meter/detector.py):** Implements the `ImageDetector` class. Houses the object detection pipeline, image preprocessing routines (Otsu thresholding, CLAHE contrast enhancement), EasyOCR reading, and spatial proximity pairing algorithms.
- **[google_auth.py](file:///C:/Users/ballt/Desktop/project/meter/google_auth.py):** Manages Google authentication, flow instantiation with PKCE, credentials verification, and session state.
- **[google_api_client.py](file:///C:/Users/ballt/Desktop/project/meter/google_api_client.py):** Wrapper client for interfacing with Google Drive API v3 and Google Sheets API v4.
- **[google_drive_handler.py](file:///C:/Users/ballt/Desktop/project/meter/google_drive_handler.py):** Coordinates high-level Google Cloud operations such as uploading processed images and saving records.
- **[templates/](file:///C:/Users/ballt/Desktop/project/meter/templates/):** Frontend UI layouts.
  - `login.html`: OAuth entry screen.
  - `index.html`: Main interactive dashboard for uploading images, reviewing detections, modifying readings, and submitting.
- **[static/](file:///C:/Users/ballt/Desktop/project/meter/static/):** Contains CSS files and client-side logic (`index.js`, `login.js`, `theme.js`).

---

## 🧠 Model Specifications & Class Mapping

The system relies on a unified YOLO model (`bestMR.pt` / `bestMR2.pt`) trained to detect utility meter parts.

| Class ID | Class Name | Description |
|---|---|---|
| **0** | `meter` | Integer portion of the utility meter reading |
| **1** | `meter1` | Decimal portion of the utility meter reading |
| **2** | `roomN` | Room number identifier |

---

## 📝 Key Coding Guidelines

1. **State Preservation:** State must be stateless or session-based. Do not create local database models (SQLite, PostgreSQL, etc.) unless requested, as data is synchronized directly to the user's personal Google Sheets ledger.
2. **Robust Preprocessing:** OCR accuracy is highly dependent on image preprocessing. When modifying crop handling in `detector.py`, ensure CLAHE and adaptive thresholding configurations are validated across light and dark modes.
3. **Thread-Safe File Cleanup:** The Flask app cleans up uploaded and processed images via asynchronous daemon threads (`schedule_file_cleanup`). Keep file cleanup safe and non-blocking.
4. **Secure Cloud Operations:** Ensure OAuth scope settings (`https://www.googleapis.com/auth/drive.file` and `https://www.googleapis.com/auth/spreadsheets`) are always matched to avoid permissions mismatches when interacting with Google APIs.
5. **No Placeholders:** If you are adding new features or visual components, avoid hardcoding mocks or placeholders. Build functional systems that plug directly into the backend routes.
