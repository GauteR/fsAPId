FROM python:3.11-slim

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config.py .
COPY start_server.py .

# Create data directory for volume mounting
RUN mkdir -p /app/data

# Create a non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Expose port for API server
EXPOSE 8000

# Create volume mount point
VOLUME ["/app/data"]

# Default to running API server, but can be overridden
CMD ["python", "start_server.py", "api", "--host", "0.0.0.0", "--port", "8000"]
