#!/usr/bin/env python3
import requests
import json
import time

# Тестируем API attendance bot
username = "a_daribayev"
password = "Qwerty51368211&"

print("🤖 Тестируем Attendance Bot API...")
print(f"Username: {username}")
print(f"Password: {password[:5]}***")

try:
    # Сначала проверим доступность API
    print("\n📡 Проверяем доступность API...")
    response = requests.get("http://localhost:8000/")
    print(f"✅ API Status: {response.status_code}")
    print(f"📄 API Response: {response.json()}")
    
    # Проверим текущий статус бота
    print("\n📊 Проверяем статус бота...")
    response = requests.get("http://localhost:8000/status")
    print(f"📄 Current Status: {response.json()}")
    
    # Запускаем attendance bot
    print(f"\n🚀 Запускаем attendance bot...")
    response = requests.get(
        "http://localhost:8000/attend",
        params={
            "username": username,
            "password": password
        },
        timeout=10  # Добавляем таймаут
    )
    
    print(f"✅ Bot Start Status: {response.status_code}")
    print(f"📄 Bot Response: {response.json()}")
    
    # Ждем немного и проверяем статус
    print("\n⏳ Ждем 5 секунд и проверяем статус...")
    time.sleep(5)
    
    response = requests.get("http://localhost:8000/status")
    print(f"📄 Bot Status: {response.json()}")
    
    print(f"\n📋 Доступные endpoints:")
    print(f"   - GET /          : Информация об API")
    print(f"   - GET /attend    : Запуск бота")
    print(f"   - GET /status    : Статус бота")
    print(f"   - GET /stop      : Остановка бота")
    
except requests.exceptions.Timeout:
    print("⏰ Таймаут запроса - это нормально для запуска бота")
except requests.exceptions.ConnectionError:
    print("❌ Ошибка: Не удается подключиться к API. Проверьте, что Docker контейнер запущен.")
except Exception as e:
    print(f"❌ Ошибка: {e}")