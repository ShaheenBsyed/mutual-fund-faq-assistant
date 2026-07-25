# Use official Python slim image for a small build footprint
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed by chromadb and sentence-transformers
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer-cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .

# Pre-download the sentence-transformer model at build time
# so the container starts instantly without a network round-trip
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Expose default port (Render overrides via $PORT env var)
EXPOSE 7860

# Use shell form so $PORT env var (injected by Render) is respected.
# Falls back to 7860 for local runs and Hugging Face Spaces.
CMD uvicorn src.phase6_app.server:app --host 0.0.0.0 --port ${PORT:-7860}
