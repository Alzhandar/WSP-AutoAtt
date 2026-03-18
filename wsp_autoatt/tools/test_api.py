#!/usr/bin/env python3
import requests
import time

from wsp_autoatt.core.settings import get_settings

SETTINGS = get_settings()
API_BASE_URL = SETTINGS.api_base_url.rstrip("/")

# Тестируем API attendance bot
username = SETTINGS.wsp_username
password = SETTINGS.wsp_password

print("Тестируем Attendance Bot API...")
print(f"Username: {username}")
print(f"Password: {password[:5]}***")

if not username or not password:
    print("WSP_USERNAME/WSP_PASSWORD не заданы в .env")
    raise SystemExit(1)

try:
    # Сначала проверим доступность API
    print("\nПроверяем доступность API...")
    response = requests.get(f"{API_BASE_URL}/")
    print(f"API Status: {response.status_code}")
    print(f"API Response: {response.json()}")
    
    # Проверим текущий статус бота
    print("\nПроверяем статус бота...")
    response = requests.get(f"{API_BASE_URL}/status")
    print(f"Current Status: {response.json()}")
    
    # Запускаем attendance bot
    print(f"\nЗапускаем attendance bot...")
    response = requests.get(
        f"{API_BASE_URL}/attend",
        params={
            "username": username,
            "password": password
        },
        timeout=10  # Добавляем таймаут
    )
    
    print(f"Bot Start Status: {response.status_code}")
    print(f"Bot Response: {response.json()}")
    
    # Ждем немного и проверяем статус
    print("\nЖдем 5 секунд и проверяем статус...")
    time.sleep(5)
    
    response = requests.get(f"{API_BASE_URL}/status")
    print(f"Bot Status: {response.json()}")
    
    print(f"\nДоступные endpoints:")
    print(f"- GET /          : Информация об API")
    print(f"- GET /attend    : Запуск бота")
    print(f"- GET /status    : Статус бота")
    print(f"- GET /stop      : Остановка бота")
    
except requests.exceptions.Timeout:
    print("Таймаут запроса - это нормально для запуска бота")
except requests.exceptions.ConnectionError:
    print("Ошибка: Не удается подключиться к API. Проверьте, что Docker контейнер запущен.")
except Exception as e:
    print(f"Ошибка: {e}")