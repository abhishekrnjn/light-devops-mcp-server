# Use a lightweight Python base image
FROM python:3.12-slim

# Install uv
RUN pip install --no-cache-dir uv

# Set workdir
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY app ./app

# Install dependencies (production only, no dev extras)
RUN uv pip install --system --no-cache .

# Expose FastAPI port
EXPOSE 8000

# Run the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
