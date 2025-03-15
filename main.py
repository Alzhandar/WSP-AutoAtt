import os
import shutil
import time
import uuid
import logging
import traceback
from datetime import datetime
from typing import Optional, List
import platform
from pathlib import Path
from dotenv import load_dotenv
import json
import base64
from io import BytesIO

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

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f"attendance_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
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
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

SCREENSHOTS_DIR = Path("screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

class AttendanceBot:    
    def __init__(self, username: str, password: str, show_ui: bool = False):
        self.username = username
        self.password = password
        self.show_ui = show_ui
        self.driver: Optional[WebDriver] = None
        self.session_dir: Optional[Path] = None
        self.debug_info = {
            "browser_errors": [],
            "page_sources": {},
            "screenshots": {},
            "attempts": {}
        }
        
    def take_screenshot(self, name: str) -> str:
        """Создает скриншот текущего состояния страницы и сохраняет его"""
        if not self.driver:
            logger.warning(f"Cannot take screenshot '{name}': driver not initialized")
            return ""
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name.replace(' ', '_')}.png"
            filepath = SCREENSHOTS_DIR / filename
            
            self.driver.save_screenshot(str(filepath))
            logger.info(f"Screenshot saved: {filepath}")
            
            if DEBUG_MODE:
                img = self.driver.get_screenshot_as_base64()
                self.debug_info["screenshots"][name] = {
                    "timestamp": timestamp,
                    "data": img[:100] + "..." if img else "failed"
                }
                
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to take screenshot '{name}': {e}")
            return ""
            
    def log_page_source(self, name: str) -> None:
        if not self.driver:
            logger.warning(f"Cannot log page source for '{name}': driver not initialized")
            return
            
        try:
            page_source = self.driver.page_source
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name.replace(' ', '_')}.html"
            filepath = SCREENSHOTS_DIR / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(page_source)
                
            logger.info(f"Page source saved: {filepath}")
            
            if DEBUG_MODE:
                truncated_html = page_source[:500] + "..." if len(page_source) > 500 else page_source
                self.debug_info["page_sources"][name] = {
                    "timestamp": timestamp,
                    "length": len(page_source),
                    "sample": truncated_html
                }
        except Exception as e:
            logger.error(f"Failed to log page source for '{name}': {e}")
    
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
        options.add_argument('--window-size=1920,1080')  
        
        logger.debug(f"Chrome options: {options.arguments}")
        
        try:
            logger.info("Creating Chrome service...")
            service = Service()
            logger.info("Initializing Chrome driver...")
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("Chrome driver initialized successfully")
            
            self.driver.implicitly_wait(5)
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Failed to initialize Chrome driver: {e}")
            logger.error(f"Error details: {error_details}")
            self.debug_info["browser_errors"].append({
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "traceback": error_details
            })
            raise
            
    def login(self) -> bool:
        logger.info("Attempting to login")
        try:
            self.take_screenshot("before_login")
            self.log_page_source("before_login")
            
            wait = WebDriverWait(self.driver, WAIT_TIME)
            
            logger.debug("Looking for username input field...")
            username_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]')))
            username_input.clear()
            username_input.send_keys(self.username)
            logger.info(f"Username entered: {self.username}")
            
            time.sleep(1)
            
            logger.debug("Looking for password input field...")
            password_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
            password_input.send_keys(self.password)
            logger.info("Password entered")
            
            logger.debug("Looking for checkbox...")
            checkbox = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="checkbox"]')))
            parent_element = self.driver.execute_script("return arguments[0].parentElement;", checkbox)
            parent_element.click()
            logger.info("Checkbox clicked")
            
            self.take_screenshot("login_form_filled")
            
            logger.debug("Looking for submit button...")
            submit_button = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@role="button" and contains(@class, "v-button-primary")]')
                )
            )
            logger.info("Submit button found, clicking...")
            submit_button.click()
            logger.info("Login form submitted")
            
            try:
                logger.debug("Waiting for login form to disappear...")
                wait.until_not(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
                logger.info("Login successful")
                self.take_screenshot("after_login")
                self.log_page_source("after_login")
                return True
            except TimeoutException:
                logger.error("Login form still present after submission, login might have failed")
                self.take_screenshot("login_failed")
                self.log_page_source("login_failed")
                return False
                
        except (TimeoutException, NoSuchElementException) as e:
            error_details = traceback.format_exc()
            logger.error(f"Login failed: {e}")
            logger.error(f"Error details: {error_details}")
            self.take_screenshot("login_error")
            self.log_page_source("login_error")
            
            self.debug_info["attempts"]["login"] = {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
                "traceback": error_details
            }
            return False
            
    def try_to_attend(self) -> int:
        if not self.driver:
            logger.error("Driver is not initialized")
            return 0
            
        wait = WebDriverWait(self.driver, WAIT_TIME)
        page_source = self.driver.page_source
        
        self.take_screenshot("before_attendance_check")
        self.log_page_source("before_attendance_check")
        
        logger.debug("Analyzing page for attendance opportunities")
        logger.debug(f"Page source length: {len(page_source)}")
        
        key_phrases = [
            "Нет доступных дисциплин", 
            "Отметиться", 
            "Вход в систему",
            "v-table-row",
            "v-button-caption"
        ]
        
        for phrase in key_phrases:
            logger.debug(f"Checking for presence of '{phrase}': {phrase in page_source}")
        
        if 'Нет доступных дисциплин' in page_source:
            logger.info("No available disciplines found")
            return 0
            
        try:
            logger.debug("Looking for 'Отметиться' buttons...")
            
            xpath_attempts = [
                "//div[span/span[@class='v-button-caption' and text()='Отметиться']]",
                "//div[.//span[contains(text(), 'Отметиться')]]",
                "//div[contains(@class, 'v-button') and .//span[contains(text(), 'Отметиться')]]",
                "//div[@role='button' and .//span[contains(text(), 'Отметиться')]]"
            ]
            
            button_divs = None
            used_xpath = ""
            
            for xpath in xpath_attempts:
                logger.debug(f"Trying XPath: {xpath}")
                elements = self.driver.find_elements(By.XPATH, xpath)
                if elements:
                    button_divs = elements
                    used_xpath = xpath
                    logger.info(f"Found {len(elements)} attendance buttons using XPath: {xpath}")
                    break
            
            if not button_divs:
                logger.warning("No attendance buttons found with any XPath attempt")
                
                all_buttons = self.driver.find_elements(By.XPATH, "//div[@role='button']")
                logger.debug(f"Total buttons found on page: {len(all_buttons)}")
                
                for i, btn in enumerate(all_buttons[:5]):
                    try:
                        text = btn.text or "no text"
                        classes = btn.get_attribute("class") or "no class"
                        logger.debug(f"Button {i+1}: text='{text}', class='{classes}'")
                    except Exception as e:
                        logger.debug(f"Error getting button {i+1} info: {e}")
                
                return 0
                
            logger.info(f"Found {len(button_divs)} attendance buttons")
            
            self.take_screenshot("attendance_buttons_found")
            
            successful_clicks = 0
            for idx, button_div in enumerate(button_divs):
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
                    
                    try:
                        button_class = button_div.get_attribute("class") or "no class"
                        button_text = button_div.text or "no text"
                        logger.debug(f"Button details: class='{button_class}', text='{button_text}'")
                    except Exception as e:
                        logger.debug(f"Error getting button details: {e}")
                    
                    self.take_screenshot(f"before_click_button_{idx+1}")
                    
                    is_displayed = button_div.is_displayed()
                    is_enabled = button_div.is_enabled()
                    logger.debug(f"Button state: displayed={is_displayed}, enabled={is_enabled}")
                    
                    if not is_displayed or not is_enabled:
                        logger.warning(f"Button for {subject_info} is not clickable: displayed={is_displayed}, enabled={is_enabled}")
                        continue
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button_div)
                    time.sleep(0.5) 
                    
                    try:
                        button_div.click()
                        logger.debug("Standard click performed")
                    except Exception as e:
                        logger.warning(f"Standard click failed: {e}, trying JS click")
                        try:
                            self.driver.execute_script("arguments[0].click();", button_div)
                            logger.debug("JavaScript click performed")
                        except Exception as e2:
                            logger.error(f"JavaScript click also failed: {e2}")
                            raise
                    
                    time.sleep(1)
                    successful_clicks += 1
                    logger.info(f"Successfully marked attendance for: {subject_info}")
                    
                    self.take_screenshot(f"after_click_button_{idx+1}")
                    
                except Exception as e:
                    error_details = traceback.format_exc()
                    logger.error(f"Failed to click attendance button: {e}")
                    logger.error(f"Error details: {error_details}")
                    self.take_screenshot(f"click_error_{idx+1}")
                    
                    self.debug_info["attempts"][f"click_{idx+1}"] = {
                        "timestamp": datetime.now().isoformat(),
                        "success": False,
                        "subject": subject_info if 'subject_info' in locals() else "Unknown",
                        "error": str(e),
                        "traceback": error_details
                    }
                    
            return successful_clicks
                
        except TimeoutException:
            logger.info("No attendance buttons found (timeout)")
            return 0
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Error during attendance check: {e}")
            logger.error(f"Error details: {error_details}")
            self.take_screenshot("attendance_check_error")
            
            self.debug_info["attempts"]["attendance_check"] = {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
                "traceback": error_details
            }
            return 0
            
    def run(self) -> None:
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
                    
                    if DEBUG_MODE:
                        try:
                            cookies = self.driver.get_cookies()
                            logger.debug(f"Current cookies: {json.dumps(cookies)}")
                        except:
                            logger.debug("Could not retrieve cookies")
                    
                    if 'Вход в систему' in page_source:
                        logger.info("Login form detected")
                        if not self.login():
                            logger.warning("Login failed, retrying in 10 seconds")
                            time.sleep(10)
                            continue
                            
                    marked_count = self.try_to_attend()
                    if marked_count > 0:
                        logger.info(f"Successfully marked attendance {marked_count} times")
                    else:
                        logger.info("No attendance marked this time")
                    
                    logger.info(f"Waiting {UPDATE_INTERVAL} seconds before refreshing...")
                    time.sleep(UPDATE_INTERVAL)
                    
                    logger.info("Refreshing page")
                    self.driver.refresh()
                    
            except WebDriverException as e:
                error_details = traceback.format_exc()
                logger.error(f"WebDriver error: {e}")
                logger.error(f"Error details: {error_details}")
                retries += 1
                
                self.debug_info["browser_errors"].append({
                    "timestamp": datetime.now().isoformat(),
                    "attempt": retries,
                    "error": str(e),
                    "traceback": error_details
                })
                
                if retries < MAX_RETRIES:
                    logger.info(f"Restarting driver (attempt {retries}/{MAX_RETRIES})")
                    self.cleanup()
                    time.sleep(5)
                    self.setup_driver()
                else:
                    logger.error(f"Maximum retries ({MAX_RETRIES}) reached, stopping bot")
                    self.save_debug_info()
                    break
                    
    def save_debug_info(self) -> None:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_info_{timestamp}.json"
            filepath = SCREENSHOTS_DIR / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.debug_info, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Debug info saved to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save debug info: {e}")
                    
    def cleanup(self) -> None:
        logger.info("Cleaning up resources...")
        
        self.save_debug_info()
        
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
    logger.info(f"Starting attendance bot for user: {username}")
    logger.info(f"Show UI: {show_ui}")
    logger.info(f"Update interval: {UPDATE_INTERVAL} seconds")
    logger.info(f"Wait time: {WAIT_TIME} seconds")
    logger.info(f"Debug mode: {DEBUG_MODE}")
    
    bot = AttendanceBot(username, password, show_ui)
    
    try:
        bot.setup_driver()
        bot.run()
    except Exception as e:
        error_details = traceback.format_exc()
        logger.critical(f"Fatal error occurred: {e}")
        logger.critical(f"Error details: {error_details}")
    finally:
        bot.cleanup()
        

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info(f"Starting attendance bot at {datetime.now().isoformat()}")
    logger.info(f"Platform: {platform.platform()}, Python: {platform.python_version()}")
    attend_bot(USERNAME, PASSWORD, SHOW_UI)