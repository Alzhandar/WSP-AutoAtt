#!/usr/bin/env python3
import requests
import time

from wsp_autoatt.core.settings import get_settings

SETTINGS = get_settings()
API_BASE_URL = SETTINGS.api_base_url.rstrip("/")

# Тестируем API attendance bot с мониторингом логов
username = SETTINGS.wsp_username
password = SETTINGS.wsp_password

def print_logs():
    """Получить и показать последние логи"""
    try:
        response = requests.get(f"{API_BASE_URL}/logs")
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                print("\n" + "="*60)
                print("ПОСЛЕДНИЕ ЛОГИ БОТА:")
                print("="*60)
                for log in data["logs"][-20:]:  # Показываем последние 20 строк
                    if log.strip():
                        print(log)
                print("="*60)
            else:
                print(f"Ошибка получения логов: {data.get('error', 'Unknown error')}")
        else:
            print(f"HTTP ошибка: {response.status_code}")
    except Exception as e:
        print(f"Ошибка при получении логов: {e}")

def monitor_bot():
    """Мониторинг работы бота в реальном времени"""
    if not username or not password:
        print("WSP_USERNAME/WSP_PASSWORD не заданы в .env")
        return

    print("Тестируем Attendance Bot API с мониторингом...")
    print(f"Username: {username}")
    print(f"Password: {password[:5]}***")

    try:
        # Проверяем доступность API
        print("\nПроверяем доступность API...")
        response = requests.get(f"{API_BASE_URL}/")
        print(f"API Status: {response.status_code}")
        print(f"API Response: {response.json()}")
        
        # Проверяем статус бота
        print("\nПроверяем статус бота...")
        response = requests.get(f"{API_BASE_URL}/status")
        current_status = response.json()
        print(f"Current Status: {current_status}")
        
        if not current_status.get("running", False):
            # Запускаем бота
            print(f"\nЗапускаем attendance bot...")
            response = requests.get(
                f"{API_BASE_URL}/attend",
                params={"username": username, "password": password},
                timeout=10
            )
            
            print(f"Bot Start Status: {response.status_code}")
            print(f"Bot Response: {response.json()}")
            
            print("\nЖдем 5 секунд для инициализации...")
            time.sleep(5)
        else:
            print("\nБот уже запущен!")
        
        # Показываем логи
        print_logs()
        
        # Предлагаем мониторинг в реальном времени
        print(f"\nХотите мониторить логи в реальном времени? (y/N): ", end="")
        choice = input().lower()
        
        if choice in ['y', 'yes', 'да', 'д']:
            print("\nМониторинг логов (Ctrl+C для выхода)...")
            try:
                while True:
                    time.sleep(10)  # Обновляем каждые 10 секунд
                    print(f"\n{time.strftime('%H:%M:%S')} - Обновление логов...")
                    print_logs()
                    
                    # Проверяем статус бота
                    response = requests.get(f"{API_BASE_URL}/status")
                    status = response.json()
                    print(f"\nСтатус бота: {'Работает' if status.get('running') else 'Остановлен'}")
                    
            except KeyboardInterrupt:
                print("\n\nМониторинг остановлен пользователем")
        
        print(f"\nДоступные endpoints:")
        print(f"- GET /          : Информация об API")
        print(f"- GET /attend    : Запуск бота")
        print(f"- GET /status    : Статус бота")
        print(f"- GET /stop      : Остановка бота")
        print(f"- GET /logs      : Просмотр логов")
        
    except requests.exceptions.Timeout:
        print("Таймаут запроса - это нормально для запуска бота")
    except requests.exceptions.ConnectionError:
        print("Ошибка: Не удается подключиться к API. Проверьте, что Docker контейнер запущен.")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    monitor_bot()