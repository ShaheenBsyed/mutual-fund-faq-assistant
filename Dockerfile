# Use official Python slim image for a small build footprint
FROM python:3.11-slim

# Set working directory
WORKDIR /app


# Copy and install Python dependencies first (layer-cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .



# Expose default port (Render overrides via $PORT env var)
EXPOSE 7860

# Use shell form so $PORT env var (injected by Render) is respected.
# Falls back to 7860 for local runs and Hugging Face Spaces.
CMD uvicorn src.phase6_app.server:app --host 0.0.0.0 --port ${PORT:-7860}
