import os
import shutil
import time
import uuid
from datetime import datetime

import psutil
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By

USERNAME = ""
PASSWORD = ""
UPDATE_INTERVAL = 60  
WAIT_TIME = 10  
SHOW_UI = False


def attend_bot(username: str, password: str):
    """Функция для запуска бота посещаемости с переданными логином и паролем"""
    global USERNAME, PASSWORD
    USERNAME = username
    PASSWORD = password
    
    print("=" * 60)
    print(f"🤖 ЗАПУСК ATTENDANCE BOT")
    print(f"👤 Пользователь: {username}")
    print(f"🕐 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    print("🔄 Завершаем существующие процессы Chrome...")
    kill_chrome_processes()
    
    options = webdriver.ChromeOptions()
    session_id = f"chrome_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    session_dir = os.path.join(os.getcwd(), "chrome_sessions", session_id)
    os.makedirs(session_dir, exist_ok=True)
    print(f"Created session directory: {session_dir}")
    
    options.add_argument(f'--user-data-dir={session_dir}')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.binary_location = "/usr/bin/chromium"  # Путь к Chromium
    
    try:
        print("🔧 Создаем Chrome service...")
        service = Service("/usr/bin/chromedriver")  # Путь к chromium-driver
        print("🚀 Инициализируем Chrome driver...")
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ Chrome driver успешно создан!")
        print("🎯 Запускаем основной цикл бота...")
        main(driver)
    except Exception as e:
        print(f"Fatal error occurred: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        print("Shutting down Chrome driver...")
        if 'driver' in locals():
            try:
                driver.quit()
            except Exception as e:
                print(f"Error while quitting driver: {e}")
        kill_chrome_processes()
        try:
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
                print(f"Removed session directory: {session_dir}")
        except Exception as e:
            print(f"Failed to remove session directory: {e}")


def kill_chrome_processes():
    for proc in psutil.process_iter():
        if proc.name() == 'chrome.exe':
            proc.kill()


def check_other_pages(selenium_driver):
    """Проверяем другие страницы для поиска дисциплин"""
    pages_to_check = [
        ("https://wsp.kbtu.kz/StudentSchedule", "Расписание студента"),
        ("https://wsp.kbtu.kz/StudentAttendance", "Посещаемость студента"), 
        ("https://wsp.kbtu.kz/RegistrationOnline", "Онлайн регистрация")
    ]
    
    current_url = selenium_driver.current_url
    
    for url, name in pages_to_check:
        try:
            print(f"  📄 Проверяем {name}: {url}")
            selenium_driver.get(url)
            time.sleep(3)
            
            page_source = selenium_driver.page_source
            title = selenium_driver.title
            
            print(f"     Заголовок: {title}")
            
            # Ищем кнопки отметиться
            if 'отметиться' in page_source.lower():
                print(f"     ✅ Найдены кнопки 'Отметиться'!")
                try_to_attend(selenium_driver)
            
            # Ищем информацию о расписании
            if any(word in page_source.lower() for word in ['расписание', 'дисциплина', 'предмет']):
                print(f"     📋 Обнаружена информация о расписании")
            
            # Проверяем на ошибки авторизации
            if 'вход в систему' in page_source.lower():
                print(f"     ⚠️ Требуется повторная авторизация")
                return False
            
        except Exception as e:
            print(f"     ❌ Ошибка при проверке {name}: {e}")
    
    # Возвращаемся на исходную страницу
    try:
        selenium_driver.get(current_url)
        time.sleep(2)
    except:
        pass
    
    return True


def try_to_attend(selenium_driver):
    wait = WebDriverWait(selenium_driver, WAIT_TIME)
    page_source = selenium_driver.page_source
    
    if 'Нет доступных дисциплин' in page_source:
        print("ℹ️  Нет доступных дисциплин для отметки посещения")
        return

    try:
        print("🔍 Ищем кнопки 'Отметиться'...")
        button_divs = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[span/span[@class='v-button-caption' and text()='Отметиться']]")
            )
        )

        if button_divs:
            print(f"🎯 Найдено {len(button_divs)} кнопок для отметки посещения")
            
            for i, button_div in enumerate(button_divs, 1):
                if button_div is not None:
                    print(f"✅ Нажимаем кнопку #{i}")
                    button_div.click()
                    print(f"   Посещение #{i} отмечено!")
                    time.sleep(1)
            
            print(f"🎉 Успешно отмечено посещение для {len(button_divs)} дисциплин!")
        else:
            print("ℹ️  Кнопки 'Отметиться' не найдены")
            
    except TimeoutException:
        print("⏰ Тайм-аут: кнопки 'Отметиться' не найдены в течение ожидаемого времени")
        return
    except Exception as e:
        print(f"❌ Ошибка при попытке отметить посещение: {e}")
        print("🔄 Повторяем попытку...")
        try_to_attend(selenium_driver)


def main(selenium_driver):
    print("🌐 Переходим на сайт WSP КБТУ...")
    selenium_driver.get("https://wsp.kbtu.kz/RegistrationOnline")
    print("✅ Сайт загружен успешно!")

    cycle_count = 0
    while True:
        cycle_count += 1
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n🔄 Цикл #{cycle_count} - {current_time}")
        
        time.sleep(1)
        page_source = selenium_driver.page_source
        
        if 'Вход в систему' in page_source:
            print("🔐 Обнаружена страница входа, выполняем авторизацию...")
            login(selenium_driver)
        else:
            print("✅ Пользователь уже авторизован")

        print("🎯 Проверяем доступные дисциплины для отметки посещения...")
        try_to_attend(selenium_driver)
        
        # Каждый 5-й цикл проверяем другие страницы
        if cycle_count % 5 == 0:
            print("🔍 Дополнительная проверка других страниц...")
            check_other_pages(selenium_driver)
        
        print(f"⏳ Ожидание {UPDATE_INTERVAL} секунд до следующей проверки...")
        time.sleep(UPDATE_INTERVAL)
        
        print("🔄 Обновляем страницу...")
        selenium_driver.refresh()


def login(selenium_driver):
    print("📝 Начинаем процесс авторизации...")
    wait = WebDriverWait(selenium_driver, WAIT_TIME)

    print("🔍 Ищем поле для логина...")
    username_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]')))
    if username_input is not None:
        username_input.clear()
        username_input.send_keys(USERNAME)
        print(f"✅ Логин введен: {USERNAME}")

    time.sleep(1)

    print("🔍 Ищем поле для пароля...")
    password_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
    if password_input is not None:
        password_input.send_keys(PASSWORD)
        print("✅ Пароль введен")

    print("☑️ Ставим галочку...")
    checkbox = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '//input[@type="checkbox"]')
        )
    )
    parent_element = selenium_driver.execute_script("return arguments[0].parentElement;", checkbox)
    if parent_element is not None:
        parent_element.click()
        print("✅ Галочка установлена")

    print("🚀 Нажимаем кнопку входа...")
    submit_button = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '//div[@role="button" and contains(@class, "v-button-primary")]')
        )
    )
    if submit_button is not None:
        submit_button.click()
        print("✅ Кнопка входа нажата")
        print("⏳ Ожидаем загрузку страницы после входа...")


def check_specific_page(url):
    """Проверить содержимое конкретной страницы"""
    print("=" * 80)
    print(f"🔍 ПРОВЕРКА СТРАНИЦЫ: {url}")
    print("=" * 80)
    
    options = webdriver.ChromeOptions()
    session_id = f"check_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    session_dir = os.path.join(os.getcwd(), "chrome_sessions", session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    options.add_argument(f'--user-data-dir={session_dir}')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.binary_location = "/usr/bin/chromium"
    
    result = {}
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Сначала авторизуемся
        print("🌐 Переходим на страницу авторизации...")
        driver.get("https://wsp.kbtu.kz/RegistrationOnline")
        time.sleep(3)
        
        # Проверяем нужна ли авторизация
        if 'Вход в систему' in driver.page_source:
            print("🔐 Выполняем авторизацию...")
            login(driver)
            time.sleep(3)
        
        # Переходим на целевую страницу
        print(f"🎯 Переходим на: {url}")
        driver.get(url)
        time.sleep(5)
        
        # Собираем информацию
        result["title"] = driver.title
        result["current_url"] = driver.current_url
        result["page_length"] = len(driver.page_source)
        
        # Получаем видимый текст
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            visible_text = body.text
            result["visible_text_preview"] = visible_text[:1000]  # Первые 1000 символов
            result["visible_text_length"] = len(visible_text)
        except Exception as e:
            result["visible_text_error"] = str(e)
        
        # Проверяем на ключевые слова расписания
        page_source = driver.page_source.lower()
        schedule_keywords = [
            "расписание", "schedule", "дисциплина", "предмет", 
            "время", "аудитория", "преподаватель", "группа",
            "понедельник", "вторник", "среда", "четверг", "пятница"
        ]
        
        found_keywords = [word for word in schedule_keywords if word in page_source]
        result["found_schedule_keywords"] = found_keywords
        
        # Проверяем структуру страницы
        result["has_tables"] = "<table" in driver.page_source
        result["has_vaadin_grid"] = "v-grid" in driver.page_source or "vaadin-grid" in driver.page_source
        result["has_buttons"] = "отметиться" in page_source
        
        # Проверяем на ошибки
        if "404" in driver.page_source or "not found" in page_source:
            result["error"] = "Page not found (404)"
        elif "403" in driver.page_source or "forbidden" in page_source:
            result["error"] = "Access forbidden (403)"
        elif "error" in page_source:
            result["error"] = "Page contains error messages"
        else:
            result["error"] = None
        
        print(f"✅ Проверка завершена")
        print(f"📄 Заголовок: {result['title']}")
        print(f"🔗 URL: {result['current_url']}")
        print(f"📊 Длина HTML: {result['page_length']} символов")
        print(f"📝 Видимый текст: {result['visible_text_length']} символов")
        print(f"🔍 Найдено ключевых слов: {len(found_keywords)}")
        
        if result["visible_text_preview"]:
            print(f"\n📋 Превью страницы (первые 500 символов):")
            print("-" * 50)
            print(result["visible_text_preview"][:500])
            print("-" * 50)
        
    except Exception as e:
        result["error"] = f"Exception: {str(e)}"
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            driver.quit()
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
        except:
            pass
    
    return result


if __name__ == "__main__":
    print("Initializing Chrome driver...")
    kill_chrome_processes()
    options = webdriver.ChromeOptions()
    session_id = f"chrome_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    session_dir = os.path.join(os.getcwd(), "chrome_sessions", session_id)
    os.makedirs(session_dir, exist_ok=True)
    print(f"Created session directory: {session_dir}")
    options.add_argument(f'--user-data-dir={session_dir}')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    if not SHOW_UI:
        print("Running in headless mode")
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.binary_location = "/usr/bin/chromium"  # Путь к Chromium
    try:
        print("Creating Chrome service...")
        service = Service("/usr/bin/chromedriver")  # Путь к chromium-driver
        print("Initializing Chrome driver...")
        driver = webdriver.Chrome(service=service, options=options)
        print("Starting bot...")
        main(driver)
    except Exception as e:
        print(f"Fatal error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Shutting down Chrome driver...")
        if 'driver' in locals():
            try:
                driver.quit()
            except Exception as e:
                print(f"Error while quitting driver: {e}")
        kill_chrome_processes()
        try:
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
                print(f"Removed session directory: {session_dir}")
        except Exception as e:
            print(f"Failed to remove session directory: {e}")