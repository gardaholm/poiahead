# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY Backend/ ./Backend/

# Copy frontend files
COPY Frontend/ ./Frontend/

# Copy startup script
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Set Python path
ENV PYTHONPATH=/app

# Expose port (fly.io will set PORT env var)
EXPOSE 8000

# Run the application using startup script
CMD ["./start.sh"]

