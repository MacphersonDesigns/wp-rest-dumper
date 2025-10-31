# WordPress REST Dumper - Docker Configuration
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for specific packages)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY wp_rest_dump.py .
COPY wp_dumper_web_gui.py .
COPY content_analytics.py .
COPY seo_analyzer.py .
COPY complete_analyzer.py .
COPY templates/ ./templates/

# Create directory for output (will be mounted as volume)
RUN mkdir -p /app/wp_dump

# Expose the web GUI port
EXPOSE 8080

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Health check to ensure the service is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Run the web GUI
CMD ["python", "wp_dumper_web_gui.py"]