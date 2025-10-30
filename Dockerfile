# Use Python 3.13 slim image as base
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Audio system dependencies
    alsa-utils \
    pulseaudio \
    portaudio19-dev \
    # Festival TTS dependencies
    festival \
    festival-dev \
    festvox-kallpc16k \
    festvox-rablpc16k \
    # Additional festival voices
    festvox-us1 \
    festvox-us2 \
    festvox-us3 \
    # System utilities
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    # D-Bus and system monitoring
    dbus \
    dbus-x11 \
    libdbus-1-dev \
    libdbus-glib-1-dev \
    python3-dbus \
    # PostgreSQL client
    postgresql-client \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash aria && \
    chown -R aria:aria /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/.cache && \
    chown -R aria:aria /app

# Switch to non-root user
USER aria

# Set up audio permissions (will need host audio access)
ENV PULSE_RUNTIME_PATH=/tmp/pulse-socket

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command
CMD ["python", "main.py"]
