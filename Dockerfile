# Use Python 3.11 image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    wget \
    curl \
    unzip \
    xvfb \
    x11-utils \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN mkdir -p /etc/apt/keyrings \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install ChromeDriver using webdriver-manager
RUN python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install(); print('ChromeDriver installed successfully')"

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p uploads chrome_profile downloads debug_screenshots

# Set environment variables
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# Create start script
RUN printf '#!/bin/bash\n\
    set -e\n\
    # Clean up any stale Xvfb lock and start virtual display if not running\n\
    if [ -e /tmp/.X99-lock ]; then rm -f /tmp/.X99-lock; fi\n\
    if ! pgrep -x Xvfb >/dev/null 2>&1; then\n\
    Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &\n\
    fi\n\
    # Wait for display to be ready\n\
    sleep 2\n\
    # Start the FastAPI application\n\
    exec python -m uvicorn api_server:app --host 0.0.0.0 --port $PORT\n' > start.sh && \
    chmod +x start.sh

EXPOSE 8000
CMD ["./start.sh"]