# آفیشل پائتھن امیج استعمال کریں
FROM python:3.10-slim

WORKDIR /app

# ضروری سسٹم لائبریریز اور Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ریلوے سرور پر کروم براؤزر (Chromium) انسٹال کرنے کی کمانڈ
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
