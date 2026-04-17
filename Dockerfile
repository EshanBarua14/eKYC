# Xpert Fintech eKYC Platform - Backend Dockerfile
FROM python:3.12-slim

# System dependencies for OpenCV + MediaPipe + Tesseract
RUN apt-get update && apt-get install -y     libglib2.0-0     libsm6     libxext6     libxrender-dev     libgomp1     tesseract-ocr     tesseract-ocr-ben     libpq-dev     gcc     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create non-root user for security
RUN useradd -m -u 1000 ekyc && chown -R ekyc:ekyc /app
USER ekyc

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
