# Use an official Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg unzip curl \
    libnss3 libxss1 libasound2 libatk1.0-0 libgtk-3-0 \
    fonts-liberation libappindicator3-1 libgbm1 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install

# Set Chrome binary location for Selenium
ENV CHROME_BIN="/usr/bin/google-chrome"

# Install pip dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose Flask port
EXPOSE ${PORT}

# Start the app
CMD ["python", "app.py"]
