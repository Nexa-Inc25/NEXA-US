#!/bin/sh
# Startup script for Streamlit UI on Render

# Debug: Show Python location
echo "Python location check:"
which python || echo "python not found"
which python3 || echo "python3 not found"
ls -la /usr/local/bin/python* || echo "No python in /usr/local/bin"

# Try multiple Python paths in order of preference
if [ -x "/usr/local/bin/python" ]; then
    echo "Using /usr/local/bin/python"
    exec /usr/local/bin/python -m streamlit run backend/pdf-service/ui.py \
        --server.port ${PORT:-8501} \
        --server.address 0.0.0.0 \
        --server.headless true
elif [ -x "/usr/local/bin/python3" ]; then
    echo "Using /usr/local/bin/python3"
    exec /usr/local/bin/python3 -m streamlit run backend/pdf-service/ui.py \
        --server.port ${PORT:-8501} \
        --server.address 0.0.0.0 \
        --server.headless true
elif command -v python >/dev/null 2>&1; then
    echo "Using python from PATH"
    exec python -m streamlit run backend/pdf-service/ui.py \
        --server.port ${PORT:-8501} \
        --server.address 0.0.0.0 \
        --server.headless true
else
    echo "ERROR: No Python interpreter found!"
    echo "PATH: $PATH"
    exit 1
fi
