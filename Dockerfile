# Use a lightweight Python base image
FROM python:3.12-slim

# Set workdir
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY mcp_http_server.py ./

# Expose FastAPI port
EXPOSE 8000

# Run the MCP HTTP server (use PORT env var if available, default to 8000)
CMD python -m uvicorn mcp_http_server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
