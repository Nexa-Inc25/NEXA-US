FROM python:3.11-slim

# Install build essentials and create symlinks for compatibility
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && ln -sf /usr/local/bin/python /usr/local/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install requirements first for better caching
COPY requirements_oct2025.txt ./requirements.txt

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir pypdf==3.17.0 && \
    pip install --no-cache-dir -r requirements.txt

# Download NLTK data if needed
RUN python -c "import nltk; nltk.download('punkt', quiet=True)" || true

# Copy application code (force rebuild with timestamp comment)
# Updated: 2025-10-13 - Using field_crew_workflow.py with security implementation
COPY field_crew_workflow.py ./field_crew_workflow.py
COPY app_oct2025_enhanced.py ./app_oct2025_enhanced.py
COPY middleware.py ./middleware.py
COPY modules ./modules

# Create necessary directories
RUN mkdir -p /tmp /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:$PATH"

# Expose port (Render sets this via $PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Use shell form to expand $PORT variable, single worker for stability
CMD ["sh", "-c", "uvicorn field_crew_workflow:api --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
