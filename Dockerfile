FROM python:3.11-slim

# Install build essentials and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip first
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY backend/pdf-service/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download NLTK data
RUN python -c "import nltk; nltk.download('punkt', quiet=True)" || true

# Copy application code
COPY backend/pdf-service ./backend/pdf-service

# Create necessary directories
RUN mkdir -p /tmp /data && chmod 755 /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/usr/local/bin:$PATH"

# CPU optimization for PyTorch
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
ENV PYTORCH_ENABLE_MPS_FALLBACK=1

# Expose correct port for API
EXPOSE 8000

# Change to app directory
WORKDIR /app/backend/pdf-service

# Run the FastAPI app with uvicorn (using simplified api.py that doesn't require OCR)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
