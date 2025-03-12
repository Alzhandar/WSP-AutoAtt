import os
import shutil
import time
import uuid
import logging
from datetime import datetime
from typing import Optional, List
import platform
from pathlib import Path
from dotenv import load_dotenv

import psutil
from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("attendance_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("attendance_bot")

BASE_URL = "https://wsp.kbtu.kz/RegistrationOnline"
USERNAME = os.getenv("USERNAME", "")
PASSWORD = os.getenv("PASSWORD", "")
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "60"))
WAIT_TIME = int(os.getenv("WAIT_TIME", "10")) 
SHOW_UI = os.getenv("SHOW_UI", "false").lower() == "true"
MAX_RETRIES = 3


class AttendanceBot:    
    def __init__(self, username: str, password: str, show_ui: bool = False):
        self.username = username
        self.password = password
        self.show_ui = show_ui
        self.driver: Optional[WebDriver] = None
        self.session_dir: Optional[Path] = None
        
    def kill_chrome_processes(self) -> None:
        chrome_process = "chrome.exe" if platform.system() == "Windows" else "Google Chrome"
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if chrome_process in proc.info['name']:
                    logger.info(f"Killing Chrome process: {proc.info['pid']}")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.warning(f"Failed to kill process: {e}")
    
    def setup_driver(self) -> None:
        logger.info("Initializing Chrome driver...")
        self.kill_chrome_processes()
        
        options = webdriver.ChromeOptions()
        session_id = f"chrome_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.session_dir = Path.cwd() / "chrome_sessions" / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created session directory: {self.session_dir}")
        
        options.add_argument(f'--user-data-dir={self.session_dir}')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        
        if not self.show_ui:
            logger.info("Running in headless mode")
            options.add_argument('--headless=new')
            
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        
        try:
            logger.info("Creating Chrome service...")
            service = Service()
            logger.info("Initializing Chrome driver...")
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
            
    def login(self) -> bool:
        logger.info("Attempting to login")
        try:
            wait = WebDriverWait(self.driver, WAIT_TIME)
            
            username_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]')))
            username_input.clear()
            username_input.send_keys(self.username)
            logger.debug("Username entered")
            
            time.sleep(1)
            
            password_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
            password_input.send_keys(self.password)
            logger.debug("Password entered")
            
            checkbox = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="checkbox"]')))
            parent_element = self.driver.execute_script("return arguments[0].parentElement;", checkbox)
            parent_element.click()
            logger.debug("Checkbox clicked")
            
            submit_button = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@role="button" and contains(@class, "v-button-primary")]')
                )
            )
            submit_button.click()
            logger.info("Login form submitted")
            
            try:
                wait.until_not(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
                logger.info("Login successful")
                return True
            except TimeoutException:
                logger.error("Login form still present after submission, login might have failed")
                return False
                
        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"Login failed: {e}")
            return False
            
    def try_to_attend(self) -> int:
        if not self.driver:
            logger.error("Driver is not initialized")
            return 0
            
        wait = WebDriverWait(self.driver, WAIT_TIME)
        page_source = self.driver.page_source
        
        if 'Нет доступных дисциплин' in page_source:
            logger.info("No available disciplines found")
            return 0
            
        try:
            button_divs = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//div[span/span[@class='v-button-caption' and text()='Отметиться']]")
                )
            )
            
            successful_clicks = 0
            for button_div in button_divs:
                try:
                    parent_row = self.driver.execute_script(
                        "return arguments[0].closest('.v-table-row')", button_div
                    )
                    subject_info = "Unknown subject"
                    if parent_row:
                        subject_cells = parent_row.find_elements(By.CLASS_NAME, "v-table-cell-content")
                        if len(subject_cells) > 0:
                            subject_info = subject_cells[0].text
                            
                    logger.info(f"Attempting to mark attendance for: {subject_info}")
                    button_div.click()
                    time.sleep(1)
                    successful_clicks += 1
                    logger.info(f"Successfully marked attendance for: {subject_info}")
                except Exception as e:
                    logger.error(f"Failed to click attendance button: {e}")
                    
            return successful_clicks
                
        except TimeoutException:
            logger.info("No attendance buttons found")
            return 0
        except Exception as e:
            logger.error(f"Error during attendance check: {e}")
            return 0
            
    def run(self) -> None:
        """Основной цикл работы бота."""
        if not self.driver:
            logger.error("Driver is not initialized")
            return
            
        logger.info(f"Navigating to {BASE_URL}")
        self.driver.get(BASE_URL)
        
        retries = 0
        while retries < MAX_RETRIES:
            try:
                while True:
                    time.sleep(1)
                    page_source = self.driver.page_source
                    
                    if 'Вход в систему' in page_source:
                        if not self.login():
                            logger.warning("Login failed, retrying in 10 seconds")
                            time.sleep(10)
                            continue
                            
                    marked_count = self.try_to_attend()
                    if marked_count > 0:
                        logger.info(f"Successfully marked attendance {marked_count} times")
                    
                    logger.info(f"Waiting {UPDATE_INTERVAL} seconds before refreshing...")
                    time.sleep(UPDATE_INTERVAL)
                    
                    logger.info("Refreshing page")
                    self.driver.refresh()
                    
            except WebDriverException as e:
                logger.error(f"WebDriver error: {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    logger.info(f"Restarting driver (attempt {retries}/{MAX_RETRIES})")
                    self.cleanup()
                    time.sleep(5)
                    self.setup_driver()
                else:
                    logger.error(f"Maximum retries ({MAX_RETRIES}) reached, stopping bot")
                    break
                    
    def cleanup(self) -> None:
        logger.info("Cleaning up resources...")
        
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver closed successfully")
            except Exception as e:
                logger.error(f"Error while quitting driver: {e}")
                
        self.kill_chrome_processes()
        
        if self.session_dir and self.session_dir.exists():
            try:
                shutil.rmtree(self.session_dir)
                logger.info(f"Removed session directory: {self.session_dir}")
            except Exception as e:
                logger.error(f"Failed to remove session directory: {e}")


def attend_bot(username: str, password: str, show_ui: bool = False) -> None:
    bot = AttendanceBot(username, password, show_ui)
    
    try:
        bot.setup_driver()
        bot.run()
    except Exception as e:
        logger.critical(f"Fatal error occurred: {e}", exc_info=True)
    finally:
        bot.cleanup()
        

if __name__ == "__main__":
    logger.info("Starting attendance bot")
    attend_bot(USERNAME, PASSWORD, SHOW_UI)