FROM python:3.11-slim

# Install build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip first
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY backend/pdf-service/requirements.txt ./backend/pdf-service/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/pdf-service/requirements.txt

# Pre-download NLTK data to avoid runtime errors
RUN python -c "import nltk; nltk.download('punkt', quiet=True)"
ENV NLTK_DATA=/app/nltk_data

# Copy application code
COPY backend/pdf-service ./backend/pdf-service

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/usr/local/bin:$PATH"

# Expose port (Render sets this via $PORT env var)
EXPOSE 8501

# Use uvicorn for FastAPI (more stable for deployments)
CMD cd backend/pdf-service && python -m uvicorn api:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1
