import cv2
import pytesseract
import re
import threading
import time
import numpy as np
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from playwright.sync_api import sync_playwright

app = FastAPI(title="Live Cricket Score API")

# یہاں وہ لنک ڈالیں جو آپ براؤزر میں اوپن کرتے ہیں (جیسے 3.tamashaweb.com والا پورا لنک)
STREAM_URL = "https://tencentcdn8.tamashaweb.com/v1/019bf00087161567ee93346674d025/019bffb7d77215fc600b1b67f81952/tmsh_srt_output_clone_720p.m3u8?timeshift=1&mode=6&delay=1800"

current_data = {
    "match": "N/A",
    "score": "N/A",
    "overs": "N/A",
    "status": "Starting...",
    "ad_running": False
}

latest_frame_bytes = None

def process_stream():
    global current_data, latest_frame_bytes
    
    with sync_playwright() as p:
        # بیک گراؤنڈ میں کروم براؤزر لانچ کریں
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = browser.new_page()
        
        try:
            print("براؤزر میں لنک اوپن ہو رہا ہے...")
            # لنک پر جائیں (60 سیکنڈ تک لوڈ ہونے کا انتظار کر سکتا ہے)
            page.goto(STREAM_URL, timeout=60000)
            
            # ویڈیو کو لوڈ ہونے اور چلنے کا ٹائم دیں (10 سیکنڈ)
            time.sleep(10)
            
            # اگر ویڈیو خودکار پلے نہیں ہوتی اور سکرین پر کلک کرنا پڑتا ہے، تو نیچے والی لائن کو ان-کمنٹ (Uncomment) کر دیں
            # page.mouse.click(500, 500)

            while True:
                # 1. براؤزر کی سکرین کا کیپچر لیں
                screenshot_bytes = page.screenshot()
                latest_frame_bytes = screenshot_bytes # یہ آپ کو /capture پر نظر آئے گا

                # 2. سکرین شاٹ کو OpenCV فارمیٹ میں بدلیں تاکہ کراپنگ ہو سکے
                nparr = np.frombuffer(screenshot_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is not None:
                    height, width, _ = frame.shape
                    # نیچے والا 25% حصہ کراپ کریں
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
                
                # 5 سیکنڈ بعد اگلا سکرین شاٹ لے گا
                time.sleep(5)

        except Exception as e:
            print("Browser Error:", e)
            current_data["status"] = f"Browser Error: {str(e)}"
        finally:
            browser.close()

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

@app.get("/capture")
def get_capture():
    if latest_frame_bytes:
        # اب چونکہ Playwright کا سکرین شاٹ PNG ہوتا ہے، اس لیے media_type image/png دیا ہے
        return Response(content=latest_frame_bytes, media_type="image/png")
    else:
        return JSONResponse(
            content={"error": "Abhi tak koi frame capture nahi hua."}, 
            status_code=404
        )
