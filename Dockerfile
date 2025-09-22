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
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list \
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
    # Start virtual display\n\
    Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &\n\
    \n\
    # Wait for display to be ready\n\
    sleep 3\n\
    \n\
    # Start the FastAPI application\n\
    exec python -m uvicorn api_server:app --host 0.0.0.0 --port $PORT\n' > start.sh && \
    chmod +x start.sh

EXPOSE 8000
CMD ["./start.sh"]