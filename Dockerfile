FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libssl-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements_security.txt ./requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY field_crew_workflow.py ./
COPY app_oct2025_enhanced.py ./
COPY middleware.py ./
COPY modules ./modules

# Create directories
RUN mkdir -p /tmp /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:$PATH"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the application
CMD ["sh", "-c", "uvicorn field_crew_workflow:api --host 0.0.0.0 --port ${PORT:-8000}"]
