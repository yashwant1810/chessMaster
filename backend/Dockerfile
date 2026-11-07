# Backend Dockerfile for Chess Review Engine
# Runs FastAPI + Stockfish in a single container

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Stockfish from Debian packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish \
    && rm -rf /var/lib/apt/lists/*

# Set Stockfish path so the app can locate the binary
ENV STOCKFISH_PATH=/usr/games/stockfish

WORKDIR /app

# Copy dependency file first for better layer caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir .

# Copy application source
COPY app/ ./app/

# Expose the API port
EXPOSE 8000

# Run the FastAPI application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
