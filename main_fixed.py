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
UPDATE_INTERVAL = 40  
WAIT_TIME = 15  # Увеличили время ожидания еще больше
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
    
    # Расширенные опции Chrome для лучшей совместимости с Ubuntu
    options.add_argument(f'--user-data-dir={session_dir}')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-iframes-during-prerender')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-logging')
    options.add_argument('--disable-dev-tools')
    options.add_argument('--remote-debugging-port=9222')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # Добавляем реалистичный User-Agent для Linux
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.binary_location = "/usr/bin/chromium"

    try:
        print("🔧 Создаем Chrome service...")
        service = Service("/usr/bin/chromedriver")
        print("🚀 Инициализируем Chrome driver...")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Убираем признаки автоматизации
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
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
        if proc.name() in ['chrome.exe', 'chromium', 'chrome']:
            proc.kill()


def try_to_attend(selenium_driver):
    """Улучшенная функция поиска и нажатия кнопок отметиться"""
    wait = WebDriverWait(selenium_driver, WAIT_TIME)
    page_source = selenium_driver.page_source
    
    print(f"🔍 Текущий URL: {selenium_driver.current_url}")
    print(f"📄 Заголовок страницы: {selenium_driver.title}")
    print(f"📊 Размер HTML: {len(page_source)} символов")
    
    if 'Нет доступных дисциплин' in page_source:
        print("ℹ️  Нет доступных дисциплин для отметки посещения")
        return

    # Проверяем наличие ключевых элементов на странице
    if 'v-button' in page_source:
        print("✅ Найдены Vaadin кнопки на странице")
    else:
        print("❌ Vaadin кнопки не найдены")
    
    if 'отметиться' in page_source.lower():
        print("✅ Текст 'отметиться' найден на странице")
    else:
        print("❌ Текст 'отметиться' не найден на странице")

    try:
        print("🔍 Ищем кнопки 'Отметиться' с расширенными селекторами...")
        
        # Множественные попытки с разными селекторами
        selectors = [
            # Оригинальный селектор
            "//div[span/span[@class='v-button-caption' and text()='Отметиться']]",
            # Более общие селекторы
            "//div[contains(@class, 'v-button') and contains(., 'Отметиться')]",
            "//span[text()='Отметиться']/ancestor::div[contains(@class, 'v-button')]",
            "//button[contains(., 'Отметиться')]",
            "//*[contains(text(), 'Отметиться') and (self::button or contains(@class, 'button') or contains(@class, 'v-button'))]",
            # Дополнительные селекторы
            "//div[@role='button' and contains(., 'Отметиться')]", 
            "//*[contains(@class, 'v-button') and .//text()[contains(., 'Отметиться')]]",
            "//span[contains(text(), 'Отметиться')]/parent::*/parent::*",
            # Селекторы через CSS
            "*[class*='v-button']:has-text('Отметиться')"
        ]
        
        button_divs = []
        successful_selector = None
        
        for i, selector in enumerate(selectors):
            try:
                print(f"   🔍 Пробуем селектор #{i+1}: {selector[:60]}...")
                
                if selector.startswith("*"):
                    # CSS селектор
                    elements = selenium_driver.find_elements(By.CSS_SELECTOR, selector.replace(":has-text('Отметиться')", ""))
                    elements = [el for el in elements if 'отметиться' in el.text.lower()]
                else:
                    # XPath селектор
                    elements = selenium_driver.find_elements(By.XPATH, selector)
                
                if elements:
                    print(f"   ✅ Найдено {len(elements)} элементов с селектором #{i+1}")
                    button_divs = elements
                    successful_selector = selector
                    break
                else:
                    print(f"   ❌ Селектор #{i+1} не дал результатов")
            except Exception as e:
                print(f"   ❌ Ошибка с селектором #{i+1}: {e}")
        
        if not button_divs:
            print("⏳ Кнопки не найдены, ждем динамической загрузки...")
            time.sleep(8)  # Увеличили время ожидания
            
            # Обновляем page_source
            page_source = selenium_driver.page_source
            
            # Попробуем еще раз с основным селектором
            try:
                button_divs = selenium_driver.find_elements(
                    By.XPATH, 
                    "//div[span/span[@class='v-button-caption' and text()='Отметиться']]"
                )
                if button_divs:
                    print(f"✅ После ожидания найдено {len(button_divs)} кнопок")
            except Exception as e:
                print(f"❌ Ошибка при повторном поиске: {e}")
        
        if not button_divs:
            print("🔍 JavaScript поиск всех кликабельных элементов...")
            try:
                js_buttons = selenium_driver.execute_script("""
                    var buttons = [];
                    var allElements = document.querySelectorAll('*');
                    for (var i = 0; i < allElements.length; i++) {
                        var elem = allElements[i];
                        var text = elem.textContent || elem.innerText || '';
                        if (text.toLowerCase().includes('отметиться')) {
                            var rect = elem.getBoundingClientRect();
                            buttons.push({
                                element: elem,
                                text: text.trim(),
                                tag: elem.tagName,
                                className: elem.className,
                                visible: rect.width > 0 && rect.height > 0,
                                clickable: elem.onclick !== null || elem.click !== undefined
                            });
                        }
                    }
                    return buttons.length;
                """)
                
                if js_buttons > 0:
                    print(f"   JavaScript нашел {js_buttons} элементов с 'отметиться'")
                    # Попробуем кликнуть через JavaScript
                    selenium_driver.execute_script("""
                        var allElements = document.querySelectorAll('*');
                        var clicked = 0;
                        for (var i = 0; i < allElements.length; i++) {
                            var elem = allElements[i];
                            var text = elem.textContent || elem.innerText || '';
                            if (text.toLowerCase().includes('отметиться') && 
                                elem.className.includes('v-button')) {
                                elem.click();
                                clicked++;
                                console.log('Clicked on:', elem);
                            }
                        }
                        return clicked;
                    """)
                    print("   ✅ Выполнен JavaScript клик по найденным элементам")
                    return
                
            except Exception as js_e:
                print(f"   ❌ Ошибка JavaScript поиска: {js_e}")
        
        # Если кнопки найдены обычным способом
        if button_divs:
            print(f"🎯 Найдено {len(button_divs)} кнопок для отметки посещения")
            print(f"🔧 Использован селектор: {successful_selector}")
            
            clicked_count = 0
            for i, button_div in enumerate(button_divs, 1):
                if button_div is not None:
                    try:
                        # Прокручиваем к элементу
                        selenium_driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button_div)
                        time.sleep(1)
                        
                        # Проверяем видимость элемента
                        if button_div.is_displayed() and button_div.is_enabled():
                            print(f"✅ Нажимаем кнопку #{i} (обычный клик)")
                            button_div.click()
                            clicked_count += 1
                            print(f"   Посещение #{i} отмечено!")
                        else:
                            print(f"⚠️  Кнопка #{i} не видна или неактивна, пробуем JS клик")
                            selenium_driver.execute_script("arguments[0].click();", button_div)
                            clicked_count += 1
                            print(f"   JS клик для кнопки #{i} выполнен!")
                        
                        time.sleep(2)  # Пауза между кликами
                        
                    except Exception as click_error:
                        print(f"❌ Ошибка при клике на кнопку #{i}: {click_error}")
            
            if clicked_count > 0:
                print(f"🎉 Успешно обработано {clicked_count} из {len(button_divs)} кнопок!")
            else:
                print("❌ Не удалось нажать ни одну кнопку")
        else:
            print("⏰ Тайм-аут: кнопки 'Отметиться' не найдены")
            
    except TimeoutException:
        print("⏰ Тайм-аут: кнопки 'Отметиться' не найдены в течение ожидаемого времени")
    except Exception as e:
        print(f"❌ Общая ошибка при попытке отметить посещение: {e}")


def main(selenium_driver):
    print("🌐 Переходим на сайт WSP КБТУ...")
    selenium_driver.get("https://pge.kbtu.kz/RegistrationOnline")
    
    # Ждем полной загрузки страницы
    print("⏳ Ожидаем полной загрузки страницы...")
    time.sleep(8)
    
    print("✅ Сайт загружен успешно!")

    cycle_count = 0
    while True:
        cycle_count += 1
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n🔄 Цикл #{cycle_count} - {current_time}")
        
        # Дополнительное ожидание для загрузки динамического контента
        time.sleep(3)
        
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
        
        # Ждем загрузки после обновления
        time.sleep(5)


def login(selenium_driver):
    print("📝 Начинаем процесс авторизации...")
    wait = WebDriverWait(selenium_driver, WAIT_TIME)

    print("🔍 Ищем поле для логина...")
    username_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]')))
    if username_input is not None:
        username_input.clear()
        username_input.send_keys(USERNAME)
        print(f"✅ Логин введен: {USERNAME}")

    time.sleep(2)

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
        
        # Ждем перенаправления после авторизации
        time.sleep(8)
        
        # Проверяем что авторизация прошла успешно
        max_attempts = 10
        for attempt in range(max_attempts):
            current_url = selenium_driver.current_url
            page_source = selenium_driver.page_source
            
            if 'Вход в систему' not in page_source:
                print("✅ Авторизация прошла успешно!")
                break
            elif attempt < max_attempts - 1:
                print(f"⏳ Попытка {attempt + 1}/{max_attempts}: все еще на странице входа, ждем...")
                time.sleep(3)
            else:
                print("❌ Не удалось авторизоваться за отведенное время")
        
        # Дополнительное ожидание для полной загрузки контента
        print("⏳ Дополнительное ожидание загрузки контента...")
        time.sleep(5)


def check_other_pages(selenium_driver):
    """Проверяем другие страницы для поиска дисциплин"""
    pages_to_check = [
        ("https://pge.kbtu.kz/StudentSchedule", "Расписание студента"),
        ("https://pge.kbtu.kz/StudentAttendance", "Посещаемость студента"), 
        ("https://pge.kbtu.kz/RegistrationOnline", "Онлайн регистрация")
    ]
    
    current_url = selenium_driver.current_url
    
    for url, name in pages_to_check:
        try:
            print(f"  📄 Проверяем {name}: {url}")
            selenium_driver.get(url)
            time.sleep(5)  # Увеличили время ожидания
            
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
        time.sleep(5)
    except:
        pass
    
    return True


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
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-iframes-during-prerender')
    options.add_argument('--window-size=1920,1080')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.binary_location = "/usr/bin/chromium"
    try:
        print("Creating Chrome service...")
        service = Service("/usr/bin/chromedriver")
        print("Initializing Chrome driver...")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Убираем признаки автоматизации
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
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