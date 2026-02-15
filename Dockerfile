# آفیشل پائتھن امیج استعمال کریں
FROM python:3.10-slim

# ڈائریکٹری سیٹ کریں
WORKDIR /app

# سسٹم کی ضروری لائبریریز اور Tesseract OCR انسٹال کریں
# (یہاں سے libgl1-mesa-glx نکال دیا گیا ہے)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ریکوائرمنٹس کاپی کر کے انسٹال کریں
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# سارا کوڈ کاپی کریں
COPY . .

# پورٹ اوپن کریں
EXPOSE 8000

# FastAPI سرور کو سٹارٹ کریں
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
