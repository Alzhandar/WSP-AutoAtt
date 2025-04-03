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


def kill_chrome_processes():
    for proc in psutil.process_iter():
        if proc.name() == 'chrome.exe':
            proc.kill()


def try_to_attend(selenium_driver):
    wait = WebDriverWait(selenium_driver, WAIT_TIME)
    page_source = selenium_driver.page_source
    if 'Нет доступных дисциплин' in page_source:
        return

    try:
        button_divs = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[span/span[@class='v-button-caption' and text()='Отметиться']]")
            )
        )

        for button_div in button_divs:
            if button_div is not None:
                button_div.click()
                time.sleep(1)
    except TimeoutException:
        return
    except Exception as e:
        print(e)
        try_to_attend(driver)


def main(selenium_driver):
    selenium_driver.get("https://wsp.kbtu.kz/RegistrationOnline")

    while True:
        time.sleep(1)
        page_source = selenium_driver.page_source
        if 'Вход в систему' in page_source:
            login(selenium_driver)

        try_to_attend(selenium_driver)
        time.sleep(UPDATE_INTERVAL)
        selenium_driver.refresh()


def login(selenium_driver):
    wait = WebDriverWait(selenium_driver, WAIT_TIME)

    username_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]')))
    if username_input is not None:
        username_input.clear()
        username_input.send_keys(USERNAME)

    time.sleep(1)

    password_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
    if password_input is not None:
        password_input.send_keys(PASSWORD)

    checkbox = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '//input[@type="checkbox"]')
        )
    )
    parent_element = selenium_driver.execute_script("return arguments[0].parentElement;", checkbox)
    if parent_element is not None:
        parent_element.click()

    submit_button = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '//div[@role="button" and contains(@class, "v-button-primary")]')
        )
    )
    if submit_button is not None:
        submit_button.click()


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
    try:
        print("Creating Chrome service...")
        service = Service()
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