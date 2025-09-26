#!/usr/bin/env python3
import requests
import json
import time
import sys

# Тестируем API attendance bot с мониторингом логов
username = "a_daribayev@kbtu.kz"
password = "Qwerty51368211&"

def print_logs():
    """Получить и показать последние логи"""
    try:
        response = requests.get("http://localhost:8000/logs")
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                print("\n" + "="*60)
                print("📋 ПОСЛЕДНИЕ ЛОГИ БОТА:")
                print("="*60)
                for log in data["logs"][-20:]:  # Показываем последние 20 строк
                    if log.strip():
                        print(log)
                print("="*60)
            else:
                print(f"❌ Ошибка получения логов: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка при получении логов: {e}")

def monitor_bot():
    """Мониторинг работы бота в реальном времени"""
    print("🤖 Тестируем Attendance Bot API с мониторингом...")
    print(f"👤 Username: {username}")
    print(f"🔐 Password: {password[:5]}***")

    try:
        # Проверяем доступность API
        print("\n📡 Проверяем доступность API...")
        response = requests.get("http://localhost:8000/")
        print(f"✅ API Status: {response.status_code}")
        print(f"📄 API Response: {response.json()}")
        
        # Проверяем статус бота
        print("\n📊 Проверяем статус бота...")
        response = requests.get("http://localhost:8000/status")
        current_status = response.json()
        print(f"📄 Current Status: {current_status}")
        
        if not current_status.get("running", False):
            # Запускаем бота
            print(f"\n🚀 Запускаем attendance bot...")
            response = requests.get(
                "http://localhost:8000/attend",
                params={"username": username, "password": password},
                timeout=10
            )
            
            print(f"✅ Bot Start Status: {response.status_code}")
            print(f"📄 Bot Response: {response.json()}")
            
            print("\n⏳ Ждем 5 секунд для инициализации...")
            time.sleep(5)
        else:
            print("\n✅ Бот уже запущен!")
        
        # Показываем логи
        print_logs()
        
        # Предлагаем мониторинг в реальном времени
        print(f"\n🔄 Хотите мониторить логи в реальном времени? (y/N): ", end="")
        choice = input().lower()
        
        if choice in ['y', 'yes', 'да', 'д']:
            print("\n🔍 Мониторинг логов (Ctrl+C для выхода)...")
            try:
                while True:
                    time.sleep(10)  # Обновляем каждые 10 секунд
                    print(f"\n⏰ {time.strftime('%H:%M:%S')} - Обновление логов...")
                    print_logs()
                    
                    # Проверяем статус бота
                    response = requests.get("http://localhost:8000/status")
                    status = response.json()
                    print(f"\n📊 Статус бота: {'🟢 Работает' if status.get('running') else '🔴 Остановлен'}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Мониторинг остановлен пользователем")
        
        print(f"\n📋 Доступные endpoints:")
        print(f"   - GET /          : Информация об API")
        print(f"   - GET /attend    : Запуск бота")
        print(f"   - GET /status    : Статус бота")
        print(f"   - GET /stop      : Остановка бота")
        print(f"   - GET /logs      : Просмотр логов")
        
    except requests.exceptions.Timeout:
        print("⏰ Таймаут запроса - это нормально для запуска бота")
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка: Не удается подключиться к API. Проверьте, что Docker контейнер запущен.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    monitor_bot()