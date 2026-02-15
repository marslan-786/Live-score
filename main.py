import cv2
import pytesseract
import re
import threading
import time
from fastapi import FastAPI

app = FastAPI(title="Live Cricket Score API")

# آپ کا لائیو سٹریم لنک
STREAM_URL = "Https://tencentcdn8.tamashaweb.com/v1/019bf00087161567ee93346674d025/019bffb7d77215fc600b1b67f81952/tmsh_srt_output_clone_720p.m3u8?timeshift=1&mode=6&delay=1800"

# گلوبل ویری ایبل جو لیٹسٹ ڈیٹا سٹور کرے گا (ایڈز کے دوران پچھلا اسکور یہیں سے جائے گا)
current_data = {
    "match": "N/A",
    "score": "N/A",
    "overs": "N/A",
    "status": "Starting...",
    "ad_running": False
}

def process_stream():
    global current_data
    while True:
        try:
            # سٹریم اوپن کریں اور صرف لیٹسٹ فریم ریڈ کریں
            cap = cv2.VideoCapture(STREAM_URL)
            ret, frame = cap.read()
            cap.release() # فوراً کلوز کر دیں تاکہ بفر نہ بنے

            if ret:
                height, width, _ = frame.shape
                # تصویر کا نیچے والا 25% حصہ کراپ کریں (جہاں اسکور ہوتا ہے)
                bottom_crop = frame[int(height * 0.75):height, 0:width]

                # تصویر کو بلیک اینڈ وائٹ اور کلیئر کریں
                gray = cv2.cvtColor(bottom_crop, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

                # Tesseract OCR سے ٹیکسٹ نکالیں
                text = pytesseract.image_to_string(thresh, config='--psm 6')

                # Regex لگا کر ڈیٹا فلٹر کریں
                score_match = re.search(r'(\d{1,3}-\d{1,2})', text)
                overs_match = re.search(r'(\d+\.\d+)', text)
                # ٹیمز کا نام نکالنے کے لیے (مثلاً NAM v USA)
                team_match = re.search(r'([A-Za-z]{3}\s*v\s*[A-Za-z]{3})', text)

                # اگر اسکور اور اوورز مل گئے ہیں (مطلب میچ چل رہا ہے)
                if score_match and overs_match:
                    current_data["score"] = score_match.group(1)
                    current_data["overs"] = overs_match.group(1)
                    if team_match:
                        current_data["match"] = team_match.group(1)
                    
                    current_data["status"] = "Live"
                    current_data["ad_running"] = False
                else:
                    # اگر اسکور نہیں ملا تو اس کا مطلب ہے ایڈ چل رہا ہے
                    current_data["status"] = "Ad or Break"
                    current_data["ad_running"] = True
                    # نوٹ: ہم اسکور اور اوورز کو اپڈیٹ نہیں کر رہے، اس لیے پرانا اسکور ہی سیو رہے گا
            
        except Exception as e:
            print("Error processing frame:", e)
        
        # 5 سیکنڈ کا وقفہ (اگلے فریم کے لیے)
        time.sleep(5)

# جیسے ہی سرور سٹارٹ ہو، بیک گراؤنڈ پروسیسنگ شروع کر دیں
@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=process_stream, daemon=True)
    thread.start()

# یوزر کے لیے API اینڈ پوائنٹ
@app.get("/api/live-score")
def get_score():
    return current_data
