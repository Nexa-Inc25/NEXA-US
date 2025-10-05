# Production Dockerfile for Render Pro deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PyMuPDF and PostgreSQL
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    mupdf-tools \
    postgresql-client \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements_complete.txt .
RUN pip install --no-cache-dir -r requirements_complete.txt

# Copy application code
COPY app_complete.py .
COPY .streamlit/ .streamlit/

# Create data directory for persistent storage
RUN mkdir -p /data /tmp

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/health || exit 1

# Start command - runs Streamlit with embedded FastAPI
CMD ["streamlit", "run", "app_complete.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true"]
