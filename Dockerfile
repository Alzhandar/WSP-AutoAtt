FROM python:3.9-slim

# Установка рабочей директории
WORKDIR /app

# Установка Chrome и необходимых зависимостей
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    procps \
    && curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установка ChromeDriver с использованием chromedriver-py
RUN pip install --no-cache-dir chromedriver-py==135.0.7049.0
RUN ln -s /usr/local/lib/python3.9/site-packages/chromedriver_py/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver

# Копирование файлов проекта
COPY req.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r req.txt

# Копирование исходного кода
COPY backend.py .
COPY main.py .

# Создание директории для сессий Chrome
RUN mkdir -p chrome_sessions

# Запуск приложения
CMD ["python", "backend.py"]