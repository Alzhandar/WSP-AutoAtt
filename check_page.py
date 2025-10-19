#!/usr/bin/env python3
import os
import shutil
import time
import uuid
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common import TimeoutException

USERNAME = "a_daribayev"
PASSWORD = "Qwerty51368211&"
WAIT_TIME = 10

def login(driver):
    """Функция для авторизации"""
    print("📝 Выполняем авторизацию...")
    wait = WebDriverWait(driver, WAIT_TIME)

    try:
        # Проверяем, нужна ли авторизация
        if 'Вход в систему' in driver.page_source:
            print("🔐 Страница входа обнаружена")
            
            username_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]')))
            username_input.clear()
            username_input.send_keys(USERNAME)
            print(f"✅ Логин введен: {USERNAME}")

            password_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
            password_input.send_keys(PASSWORD)
            print("✅ Пароль введен")

            checkbox = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="checkbox"]')))
            parent_element = driver.execute_script("return arguments[0].parentElement;", checkbox)
            parent_element.click()
            print("✅ Галочка установлена")

            submit_button = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@role="button" and contains(@class, "v-button-primary")]')))
            submit_button.click()
            print("✅ Кнопка входа нажата")
            
            # Ждем загрузки после входа
            time.sleep(3)
            print("⏳ Ожидаем загрузку после авторизации...")
        else:
            print("✅ Уже авторизованы")
            
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        return False
    
    return True

def check_page_content(url):
    """Проверяем содержимое страницы"""
    print("=" * 80)
    print(f"🔍 ПРОВЕРКА СОДЕРЖИМОГО СТРАНИЦЫ: {url}")
    print("=" * 80)
    
    # Настройка Chrome
    options = webdriver.ChromeOptions()
    session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_dir = os.path.join(os.getcwd(), "test_sessions", session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    options.add_argument(f'--user-data-dir={session_dir}')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--headless=new')  # Headless режим
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    
    try:
        # На macOS используем стандартный chromedriver
        print("🔧 Инициализируем Chrome driver...")
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        
        # Сначала идем на главную страницу для авторизации
        print("🌐 Переходим на главную страницу WSP...")
        driver.get("https://wsp.kbtu.kz/RegistrationOnline")
        time.sleep(3)
        
        # Авторизуемся
        if not login(driver):
            print("❌ Не удалось авторизоваться")
            return
        
        # Теперь переходим на целевую страницу
        print(f"🎯 Переходим на: {url}")
        driver.get(url)
        time.sleep(5)  # Ждем загрузки страницы
        
        # Получаем заголовок страницы
        title = driver.title
        print(f"📄 Заголовок страницы: {title}")
        
        # Получаем текущий URL
        current_url = driver.current_url
        print(f"🔗 Текущий URL: {current_url}")
        
        # Получаем содержимое страницы
        page_source = driver.page_source
        
        # Анализируем содержимое
        print("\n" + "="*60)
        print("📋 АНАЛИЗ СОДЕРЖИМОГО СТРАНИЦЫ:")
        print("="*60)
        
        # Проверяем на ошибки
        if "404" in page_source or "Not Found" in page_source:
            print("❌ Страница не найдена (404)")
        elif "403" in page_source or "Forbidden" in page_source:
            print("❌ Доступ запрещен (403)")
        elif "error" in page_source.lower():
            print("⚠️  На странице обнаружены ошибки")
        else:
            print("✅ Страница загружена без явных ошибок")
        
        # Ищем ключевые элементы
        keywords = [
            "расписание", "schedule", "дисциплина", "предмет", "время", 
            "аудитория", "преподаватель", "группа", "студент"
        ]
        
        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in page_source.lower():
                found_keywords.append(keyword)
        
        if found_keywords:
            print(f"🔍 Найденные ключевые слова: {', '.join(found_keywords)}")
        else:
            print("🔍 Ключевые слова не найдены")
        
        # Ищем таблицы или списки
        if "<table" in page_source:
            table_count = page_source.count("<table")
            print(f"📊 Найдено таблиц: {table_count}")
        
        if "v-grid" in page_source or "vaadin-grid" in page_source:
            print("📊 Обнаружена Vaadin Grid (таблица данных)")
        
        # Проверяем на наличие данных расписания
        schedule_indicators = [
            "понедельник", "вторник", "среда", "четверг", "пятница", "суббота",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
            "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"
        ]
        
        found_schedule = []
        for indicator in schedule_indicators:
            if indicator.lower() in page_source.lower():
                found_schedule.append(indicator)
        
        if found_schedule:
            print(f"📅 Найдены элементы расписания: {', '.join(found_schedule[:5])}")
        
        # Показываем первые 500 символов видимого текста
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            visible_text = body.text[:500]
            print(f"\n📄 Первые 500 символов страницы:")
            print("-" * 40)
            print(visible_text)
            print("-" * 40)
        except Exception as e:
            print(f"⚠️  Не удалось получить видимый текст: {e}")
        
        # Сохраняем HTML в файл для анализа
        html_file = f"page_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(page_source)
        print(f"\n💾 HTML сохранен в файл: {html_file}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            driver.quit()
            # Удаляем временную сессию
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
        except:
            pass

if __name__ == "__main__":
    # Проверяем страницу расписания студента
    check_page_content("https://wsp.kbtu.kz/StudentSchedule")