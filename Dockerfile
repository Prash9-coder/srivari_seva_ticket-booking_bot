# Use Python 3.11 image
FROM python:3.11

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    wget \
    curl \
    unzip \
    xvfb \
    x11-utils && \
    rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN curl -fsSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb && \
    apt-get update && \
    apt-get install -y ./chrome.deb && \
    rm chrome.deb && \
    rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    curl -fsSL http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip -o chromedriver.zip && \
    unzip chromedriver.zip && \
    mv chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm chromedriver.zip

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p uploads chrome_profile downloads debug_screenshots

# Set environment variables
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# Start script
RUN printf '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &\nsleep 3\nexec python -m uvicorn api_server:app --host 0.0.0.0 --port $PORT\n' > start.sh && \
    chmod +x start.sh

EXPOSE 8000
CMD ["./start.sh"]