# RoomMeterApp - AI-Powered Room & Meter Recognition

This application automates the process of reading room numbers and utility meter values from images, storing the results in Google Sheets and images in Google Drive. It leverages YOLO for object detection and EasyOCR for text recognition.

## Project Overview

-   **Purpose:** Automated detection and recording of utility meter readings associated with specific room numbers.
-   **Core Technologies:**
    -   **Backend:** Python, Flask
    -   **Computer Vision:** YOLO (via `ultralytics`), EasyOCR, OpenCV
    -   **Cloud Integration:** Google Drive API, Google Sheets API (OAuth2 PKCE)
    -   **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS

## Architecture

1.  **Web Server (`app.py`):** Flask application handling routing, file uploads, and session management.
2.  **Authentication (`google_auth.py`):** Handles Google OAuth2 flow using PKCE for secure client-side integration.
3.  **Detector (`detector.py`):**
    -   Uses a unified YOLO model (`bestMR.pt`) to detect three classes: `meter` (integer part), `meter1` (decimal part), and `roomN` (room number).
    -   Employs advanced image preprocessing (CLAHE, thresholding, rotation) to improve OCR accuracy.
    -   Runs EasyOCR with multiple configurations in parallel to find the best text match.
    -   Implements **Proximity Matching** to pair room numbers with their corresponding meters based on spatial distance in the image.
4.  **Google Integration (`google_api_client.py`, `google_drive_handler.py`):**
    -   Automatically creates a `RoomMeterApp` folder structure in the user's Google Drive.
    -   Uploads processed images with bounding box overlays.
    -   Appends detection data (Timestamp, Room, Meter, Full Reading, Drive Link) to a Google Sheet named `RoomMeterData`.

## Building and Running

### Prerequisites
-   Python 3.10+
-   Google Cloud Project with Drive and Sheets APIs enabled.
-   `client_secret.json` or equivalent environment variables.

### Installation
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```powershell
# Ensure .env file is configured with SECRET_KEY and GOOGLE_CLIENT_SECRET
python app.py
```
The app runs by default on `http://localhost:8080`.

## Development Conventions

-   **Image Processing:** Use the `ImageDetector` class for all CV tasks. It handles model loading and hardware acceleration (GPU if available).
-   **Security:**
    -   **PKCE:** Always persist the `code_verifier` in the session during OAuth flow.
    -   **Cleanup:** Uploaded files and processed results are automatically deleted after 60 seconds (managed by `schedule_file_cleanup`).
-   **Frontend:**
    -   Prefer Vanilla JavaScript for interactivity.
    -   Styles are managed via Tailwind CSS and local CSS files in `static/css/`.
    -   The UI supports a "Dark/Light" theme toggle (`theme.js`).
-   **Validation:** A recording is only considered "valid" for automatic upload if both a Room Number and a Meter Reading are detected and paired successfully. Users can manually edit values before saving to Sheets.

## Key Files
-   `app.py`: Main entry point and Flask routes.
-   `detector.py`: Core CV logic (YOLO + EasyOCR + Proximity Matching).
-   `google_auth.py`: OAuth2 authentication management.
-   `bestMR.pt`: Pre-trained YOLO model weight.
-   `static/js/index.js`: Frontend logic for uploads, previews, and API interaction.
