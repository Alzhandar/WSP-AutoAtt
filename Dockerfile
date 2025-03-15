FROM python:3.10-slim

ENV TZ=Asia/Almaty
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libxss1 \
    libnss3 \
    libnspr4 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libu2f-udev \
    libvulkan1 \
    psmisc \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        echo "ARM64 architecture detected, using Chromium instead of Chrome..." && \
        apt-get update && \
        apt-get install -y chromium chromium-driver && \
        ln -s /usr/bin/chromium /usr/bin/google-chrome && \
        apt-get clean; \
    else \
        echo "AMD64 architecture detected, installing Google Chrome..." && \
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-keyring.gpg && \
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
        apt-get update && \
        apt-get install -y google-chrome-stable && \
        apt-get clean; \
    fi

RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        echo "Using pre-installed ChromeDriver for ARM64"; \
    else \
        CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1) && \
        echo "Chrome major version: ${CHROME_VERSION}" && \
        CHROMEDRIVER_VERSION="134.0.6998.49" && \
        echo "Using ChromeDriver version: ${CHROMEDRIVER_VERSION}" && \
        wget -q -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" && \
        unzip /tmp/chromedriver.zip -d /tmp/ && \
        cp /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ && \
        chmod +x /usr/local/bin/chromedriver && \
        rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64; \
    fi

WORKDIR /app

COPY req.txt .

RUN pip install --no-cache-dir psutil==5.9.6 && \
    pip install --no-cache-dir -r req.txt

RUN pip install --no-cache-dir \
    selenium-wire \
    webdriver_manager

COPY . .

RUN mkdir -p /app/logs /app/chrome_sessions /app/screenshots /app/api_logs
RUN chmod -R 777 /app/logs /app/chrome_sessions /app/screenshots /app/api_logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DISPLAY=:99

CMD ["python", "backend.py"]