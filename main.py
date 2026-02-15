import cv2
import pytesseract
import re
import threading
import time
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="Live Cricket Score API")

# آپ کا لائیو سٹریم لنک
STREAM_URL = "Https://tencentcdn8.tamashaweb.com/v1/019bf00087161567ee93346674d025/019bffb7d77215fc600b1b67f81952/tmsh_srt_output_clone_720p.m3u8?timeshift=1&mode=6&delay=1800"

current_data = {
    "match": "N/A",
    "score": "N/A",
    "overs": "N/A",
    "status": "Starting...",
    "ad_running": False
}

# لیٹسٹ کیپچر کی گئی تصویر کو میموری میں رکھنے کے لیے ویری ایبل
latest_frame_bytes = None

def process_stream():
    global current_data, latest_frame_bytes
    while True:
        try:
            # سٹریم اوپن کریں اور فریم ریڈ کریں
            cap = cv2.VideoCapture(STREAM_URL)
            ret, frame = cap.read()
            cap.release()

            if ret:
                # 1. سب سے پہلے تصویر کو /capture روٹ کے لیے سیو کریں
                # یہ پرانی تصویر کو ہٹا کر نئی تصویر سیٹ کر دے گا
                _, buffer = cv2.imencode('.jpg', frame)
                latest_frame_bytes = buffer.tobytes()

                # 2. اب اسکور پڑھنے کے لیے کراپنگ اور پروسیسنگ کریں
                height, width, _ = frame.shape
                bottom_crop = frame[int(height * 0.75):height, 0:width]

                gray = cv2.cvtColor(bottom_crop, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

                text = pytesseract.image_to_string(thresh, config='--psm 6')

                score_match = re.search(r'(\d{1,3}-\d{1,2})', text)
                overs_match = re.search(r'(\d+\.\d+)', text)
                team_match = re.search(r'([A-Za-z]{3}\s*v\s*[A-Za-z]{3})', text)

                if score_match and overs_match:
                    current_data["score"] = score_match.group(1)
                    current_data["overs"] = overs_match.group(1)
                    if team_match:
                        current_data["match"] = team_match.group(1)
                    current_data["status"] = "Live"
                    current_data["ad_running"] = False
                else:
                    current_data["status"] = "Ad or Break (No Score Found)"
                    current_data["ad_running"] = True
            else:
                current_data["status"] = "Error: Stream link not working or blocked"
                
        except Exception as e:
            print("Error processing frame:", e)
            current_data["status"] = f"Error: {str(e)}"
        
        time.sleep(5)

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=process_stream, daemon=True)
    thread.start()

@app.get("/")
def health_check():
    return {
        "status": "Server is Running!",
        "Live Score API": "/api/live-score",
        "View Live Capture": "/capture"
    }

@app.get("/api/live-score")
def get_score():
    return current_data

# یہ نیا روٹ ہے جو آپ کو لیٹسٹ تصویر دکھائے گا
@app.get("/capture")
def get_capture():
    if latest_frame_bytes:
        # براؤزر کو بتائیں کہ یہ کوئی ٹیکسٹ نہیں بلکہ JPEG تصویر ہے
        return Response(content=latest_frame_bytes, media_type="image/jpeg")
    else:
        return JSONResponse(
            content={"error": "Abhi tak koi frame capture nahi hua, ya stream link block hai."}, 
            status_code=404
        )
