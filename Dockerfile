# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies for Chrome and Xvfb (virtual display)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROME_DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE") \
    && wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm /tmp/chromedriver.zip

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p uploads chrome_profile downloads debug_screenshots

# Set environment variables
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# Create startup script
RUN echo '#!/bin/bash\n\
    # Start virtual display\n\
    Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &\n\
    # Wait for Xvfb to start\n\
    sleep 2\n\
    # Start the application\n\
    python -m uvicorn api_server:app --host 0.0.0.0 --port $PORT\n\
    ' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Start the application
CMD ["/app/start.sh"]