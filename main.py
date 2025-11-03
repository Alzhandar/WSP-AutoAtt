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
WAIT_TIME = 10  # Увеличили время ожидания
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
    # Добавляем реалистичный User-Agent
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.binary_location = "/usr/bin/chromium"  # Путь к Chromium
    
    try:
        print("🔧 Создаем Chrome service...")
        service = Service("/usr/bin/chromedriver")  # Путь к chromium-driver
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
        if proc.name() == 'chrome.exe':
            proc.kill()


def save_debug_screenshot(driver, name="debug"):
    """Сохраняет скриншот для отладки"""
    try:
        screenshot_path = f"/tmp/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        driver.save_screenshot(screenshot_path)
        print(f"📷 Скриншот сохранен: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"❌ Ошибка при сохранении скриншота: {e}")
        return None


def save_page_source(driver, name="debug"):
    """Сохраняет HTML исходник страницы для отладки"""
    try:
        html_path = f"/tmp/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"📄 HTML сохранен: {html_path}")
        return html_path
    except Exception as e:
        print(f"❌ Ошибка при сохранении HTML: {e}")
        return None


def analyze_current_page(driver):
    """Анализирует текущую страницу и выводит полезную информацию"""
    try:
        url = driver.current_url
        title = driver.title
        page_source = driver.page_source
        
        print(f"🔍 АНАЛИЗ ТЕКУЩЕЙ СТРАНИЦЫ:")
        print(f"   📍 URL: {url}")
        print(f"   📄 Заголовок: {title}")
        print(f"   📊 Размер HTML: {len(page_source)} символов")
        
        # Проверяем ключевые элементы
        key_checks = {
            "Страница входа": "Вход в систему" in page_source,
            "Vaadin фреймворк": "vaadin" in page_source.lower(),
            "Кнопки": "button" in page_source.lower() or "v-button" in page_source.lower(),
            "Текст 'Отметиться'": "отметиться" in page_source.lower(),
            "Расписание": any(word in page_source.lower() for word in ["расписание", "дисциплин", "предмет"]),
            "JavaScript ошибки": "error" in page_source.lower() and "javascript" in page_source.lower(),
        }
        
        for check_name, result in key_checks.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
        
        # Получаем видимый текст страницы
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            visible_text = body.text
            print(f"   📝 Видимый текст: {len(visible_text)} символов")
            
            # Показываем первые 200 символов видимого текста
            if visible_text:
                preview = visible_text.replace('\n', ' ').strip()[:200]
                print(f"   👁️  Превью: {preview}...")
        except Exception as e:
            print(f"   ❌ Ошибка получения видимого текста: {e}")
            
    except Exception as e:
        print(f"❌ Ошибка анализа страницы: {e}")


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
            time.sleep(2)
            
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

    # Дополнительная отладочная информация
    print(f"🔍 Текущий URL: {selenium_driver.current_url}")
    print(f"📄 Заголовок страницы: {selenium_driver.title}")
    print(f"📊 Размер HTML: {len(page_source)} символов")
    
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
        print("🔍 Ищем кнопки 'Отметиться'...")
        
        # Пробуем несколько различных селекторов
        selectors = [
            "//div[span/span[@class='v-button-caption' and text()='Отметиться']]",
            "//div[contains(@class, 'v-button') and contains(., 'Отметиться')]",
            "//span[text()='Отметиться']/ancestor::div[contains(@class, 'v-button')]",
            "//button[contains(., 'Отметиться')]",
            "//*[contains(text(), 'Отметиться') and (self::button or contains(@class, 'button') or contains(@class, 'v-button'))]"
        ]
        
        button_divs = []
        for i, selector in enumerate(selectors):
            try:
                print(f"   Пробуем селектор #{i+1}: {selector[:50]}...")
                elements = selenium_driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"   ✅ Найдено {len(elements)} элементов с селектором #{i+1}")
                    button_divs = elements
                    break
                else:
                    print(f"   ❌ Селектор #{i+1} не дал результатов")
            except Exception as e:
                print(f"   ❌ Ошибка с селектором #{i+1}: {e}")
        
        if not button_divs:
            # Попробуем подождать дольше для динамической загрузки
            print("⏳ Ждем динамической загрузки контента...")
            time.sleep(5)
            
            # Сохраняем отладочную информацию
            save_debug_screenshot(selenium_driver, "no_buttons_found")
            save_page_source(selenium_driver, "no_buttons_found")
            
            # Пробуем еще раз с ожиданием
            try:
                button_divs = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//div[span/span[@class='v-button-caption' and text()='Отметиться']]")
                    )
                )
            except TimeoutException:
                print("⏰ Тайм-аут при ожидании кнопок")
                
                # Дополнительная отладочная информация
                print("🔍 Поиск всех кнопок на странице...")
                all_buttons = selenium_driver.find_elements(By.XPATH, "//button | //*[contains(@class, 'button')] | //*[contains(@class, 'v-button')]")
                print(f"   Найдено всего кнопок: {len(all_buttons)}")
                
                for i, btn in enumerate(all_buttons[:10]):  # Показываем первые 10
                    try:
                        text = btn.text.strip()
                        classes = btn.get_attribute('class')
                        print(f"   Кнопка {i+1}: '{text}' (классы: {classes})")
                    except:
                        print(f"   Кнопка {i+1}: <не удалось получить информацию>")
                
                # Поиск всех элементов с текстом "отметиться"
                print("🔍 Поиск всех элементов с текстом 'Отметиться'...")
                attend_elements = selenium_driver.find_elements(By.XPATH, "//*[contains(text(), 'Отметиться')]")
                print(f"   Найдено элементов: {len(attend_elements)}")
                
                for i, elem in enumerate(attend_elements):
                    try:
                        tag = elem.tag_name
                        text = elem.text.strip()
                        classes = elem.get_attribute('class')
                        print(f"   Элемент {i+1}: <{tag}> '{text}' (классы: {classes})")
                    except:
                        print(f"   Элемент {i+1}: <не удалось получить информацию>")
                
                # Последняя попытка - JavaScript поиск
                print("🔍 JavaScript поиск кнопок...")
                try:
                    js_result = selenium_driver.execute_script("""
                        var buttons = [];
                        var allElements = document.querySelectorAll('*');
                        for (var i = 0; i < allElements.length; i++) {
                            var elem = allElements[i];
                            if (elem.textContent && elem.textContent.toLowerCase().includes('отметиться')) {
                                buttons.push({
                                    tag: elem.tagName,
                                    text: elem.textContent.trim(),
                                    className: elem.className,
                                    clickable: elem.onclick !== null || elem.addEventListener !== undefined
                                });
                            }
                        }
                        return buttons;
                    """)
                    
                    if js_result:
                        print(f"   JavaScript нашел {len(js_result)} элементов:")
                        for i, btn_info in enumerate(js_result):
                            print(f"   Элемент {i+1}: {btn_info}")
                    else:
                        print("   JavaScript не нашел элементов с 'отметиться'")
                        
                except Exception as js_e:
                    print(f"   Ошибка JavaScript поиска: {js_e}")

        if button_divs:
            print(f"🎯 Найдено {len(button_divs)} кнопок для отметки посещения")
            
            for i, button_div in enumerate(button_divs, 1):
                if button_div is not None:
                    try:
                        # Прокручиваем к элементу перед кликом
                        selenium_driver.execute_script("arguments[0].scrollIntoView(true);", button_div)
                        time.sleep(1)
                        
                        # Пробуем обычный клик
                        print(f"✅ Нажимаем кнопку #{i}")
                        button_div.click()
                        print(f"   Посещение #{i} отмечено!")
                        time.sleep(2)
                        
                    except Exception as click_error:
                        print(f"❌ Ошибка при клике на кнопку #{i}: {click_error}")
                        
                        # Пробуем JavaScript клик
                        try:
                            print(f"   Пробуем JavaScript клик для кнопки #{i}")
                            selenium_driver.execute_script("arguments[0].click();", button_div)
                            print(f"   JavaScript клик успешен для кнопки #{i}")
                            time.sleep(2)
                        except Exception as js_error:
                            print(f"   ❌ JavaScript клик тоже не сработал: {js_error}")
            
            print(f"🎉 Обработано {len(button_divs)} кнопок!")
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
    selenium_driver.get("https://pge.kbtu.kz/RegistrationOnline")
    
    # Ждем полной загрузки страницы
    print("⏳ Ожидаем полной загрузки страницы...")
    time.sleep(5)
    
    print("✅ Сайт загружен успешно!")

    cycle_count = 0
    while True:
        cycle_count += 1
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n🔄 Цикл #{cycle_count} - {current_time}")
        
        # Дополнительное ожидание для загрузки динамического контента
        time.sleep(2)
        
        page_source = selenium_driver.page_source
        
        if 'Вход в систему' in page_source:
            print("🔐 Обнаружена страница входа, выполняем авторизацию...")
            login(selenium_driver)
        else:
            print("✅ Пользователь уже авторизован")

        # Каждый 10-й цикл делаем детальный анализ страницы
        if cycle_count % 10 == 0:
            analyze_current_page(selenium_driver)

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
        time.sleep(3)


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
        
        # Ждем перенаправления после авторизации
        time.sleep(5)
        
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
                time.sleep(2)
            else:
                print("❌ Не удалось авторизоваться за отведенное время")
        
        # Дополнительное ожидание для полной загрузки контента
        print("⏳ Дополнительное ожидание загрузки контента...")
        time.sleep(3)


def run_debug_session(username: str, password: str):
    """Запускает отладочную сессию для диагностики проблем"""
    print("=" * 80)
    print(f"🐛 ОТЛАДОЧНАЯ СЕССИЯ")
    print(f"👤 Пользователь: {username}")
    print("=" * 80)
    
    kill_chrome_processes()
    
    options = webdriver.ChromeOptions()
    session_id = f"debug_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    session_dir = os.path.join(os.getcwd(), "chrome_sessions", session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # Настройки браузера
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
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.binary_location = "/usr/bin/chromium"
    
    result = {
        "session_id": session_id,
        "steps": [],
        "errors": [],
        "screenshots": [],
        "html_files": []
    }
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Убираем признаки автоматизации
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        result["steps"].append("Браузер запущен успешно")
        
        # Шаг 1: Переход на сайт
        print("🌐 Переходим на сайт...")
        driver.get("https://pge.kbtu.kz/RegistrationOnline")
        time.sleep(5)
        
        result["steps"].append(f"Переход на сайт: {driver.current_url}")
        analyze_current_page(driver)
        
        screenshot_path = save_debug_screenshot(driver, "step1_initial_page")
        html_path = save_page_source(driver, "step1_initial_page")
        if screenshot_path:
            result["screenshots"].append(screenshot_path)
        if html_path:
            result["html_files"].append(html_path)
        
        # Шаг 2: Авторизация
        if 'Вход в систему' in driver.page_source:
            print("🔐 Выполняем авторизацию...")
            result["steps"].append("Найдена страница входа")
            
            # Устанавливаем глобальные переменные для функции login
            global USERNAME, PASSWORD
            USERNAME = username
            PASSWORD = password
            
            login(driver)
            
            screenshot_path = save_debug_screenshot(driver, "step2_after_login")
            html_path = save_page_source(driver, "step2_after_login")
            if screenshot_path:
                result["screenshots"].append(screenshot_path)
            if html_path:
                result["html_files"].append(html_path)
                
            result["steps"].append("Авторизация выполнена")
        else:
            result["steps"].append("Авторизация не требуется")
        
        # Шаг 3: Анализ основной страницы
        print("🔍 Анализируем основную страницу...")
        analyze_current_page(driver)
        
        # Шаг 4: Поиск кнопок отметиться
        print("🎯 Поиск кнопок 'Отметиться'...")
        page_source = driver.page_source
        
        # Различные проверки
        checks = {
            "has_otmetitsya_text": "отметиться" in page_source.lower(),
            "has_vaadin_buttons": "v-button" in page_source,
            "has_any_buttons": "button" in page_source.lower(),
            "page_size": len(page_source),
            "has_schedule_words": any(word in page_source.lower() for word in ["расписание", "дисциплин", "предмет"])
        }
        
        result["checks"] = checks
        
        # Пробуем найти кнопки разными способами
        selectors_tested = []
        selectors = [
            "//div[span/span[@class='v-button-caption' and text()='Отметиться']]",
            "//div[contains(@class, 'v-button') and contains(., 'Отметиться')]",
            "//span[text()='Отметиться']/ancestor::div[contains(@class, 'v-button')]",
            "//button[contains(., 'Отметиться')]",
            "//*[contains(text(), 'Отметиться')]"
        ]
        
        for i, selector in enumerate(selectors):
            try:
                elements = driver.find_elements(By.XPATH, selector)
                selectors_tested.append({
                    "selector": selector,
                    "found": len(elements),
                    "success": len(elements) > 0
                })
                if elements:
                    result["steps"].append(f"Найдено {len(elements)} кнопок с селектором #{i+1}")
                    break
            except Exception as e:
                selectors_tested.append({
                    "selector": selector,
                    "found": 0,
                    "success": False,
                    "error": str(e)
                })
        
        result["selectors_tested"] = selectors_tested
        
        # Шаг 5: Проверка других страниц
        pages_to_check = [
            "https://pge.kbtu.kz/StudentSchedule",
            "https://pge.kbtu.kz/StudentAttendance"
        ]
        
        other_pages_results = []
        for page_url in pages_to_check:
            try:
                print(f"📄 Проверяем страницу: {page_url}")
                driver.get(page_url)
                time.sleep(3)
                
                page_result = {
                    "url": page_url,
                    "title": driver.title,
                    "has_otmetitsya": "отметиться" in driver.page_source.lower(),
                    "page_size": len(driver.page_source)
                }
                
                other_pages_results.append(page_result)
                
                screenshot_path = save_debug_screenshot(driver, f"page_{page_url.split('/')[-1]}")
                if screenshot_path:
                    result["screenshots"].append(screenshot_path)
                    
            except Exception as e:
                other_pages_results.append({
                    "url": page_url,
                    "error": str(e)
                })
        
        result["other_pages"] = other_pages_results
        result["steps"].append("Отладочная сессия завершена успешно")
        
    except Exception as e:
        error_msg = f"Ошибка в отладочной сессии: {str(e)}"
        print(f"❌ {error_msg}")
        result["errors"].append(error_msg)
        import traceback
        result["traceback"] = traceback.format_exc()
    
    finally:
        try:
            if 'driver' in locals():
                driver.quit()
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
        except:
            pass
    
    return result


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
    
    result = {}
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Убираем признаки автоматизации
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        # Сначала авторизуемся
        print("🌐 Переходим на страницу авторизации...")
        driver.get("https://pge.kbtu.kz/RegistrationOnline")
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
    options.binary_location = "/usr/bin/chromium"  # Путь к Chromium
    try:
        print("Creating Chrome service...")
        service = Service("/usr/bin/chromedriver")  # Путь к chromium-driver
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