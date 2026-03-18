FROM python:3.9-slim

# Установка рабочей директории
WORKDIR /app

# Установка Chromium и необходимых зависимостей (работает на ARM64)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    procps \
    chromium \
    chromium-driver \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ChromeDriver уже установлен как chromium-driver

# Копирование файлов проекта
COPY req.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r req.txt

# Копирование исходного кода
COPY wsp_autoatt ./wsp_autoatt
COPY backend.py .
COPY main.py .

# Создание директории для сессий Chrome
RUN mkdir -p chrome_sessions

# Копирование скрипта запуска
COPY start.sh .
RUN chmod +x start.sh

# Устанавливаем переменные среды
ENV DISPLAY=:99
ENV PYTHONPATH=/app

# Запуск приложения с Xvfb
CMD ["./start.sh", "-m", "wsp_autoatt.api"]