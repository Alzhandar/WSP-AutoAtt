import logging
import os
import threading
import traceback
import json
from datetime import datetime
from typing import Dict, Optional, Any
import time

import uvicorn
from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from main import attend_bot, AttendanceBot, USERNAME, PASSWORD, BASE_URL

load_dotenv()

logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_logs")
os.makedirs(logs_dir, exist_ok=True)

log_filename = os.path.join(logs_dir, f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("attendance_api")

app = FastAPI(
    title="Attendance Bot API",
    description="API для автоматической отметки посещаемости",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AttendanceRequest(BaseModel):
    username: str = Field(..., description="Имя пользователя для входа в систему")
    password: str = Field(..., description="Пароль пользователя")
    show_ui: bool = Field(False, description="Показывать ли интерфейс браузера")

class AuthCheckRequest(BaseModel):
    username: str = Field(..., description="Имя пользователя для проверки авторизации")
    password: str = Field(..., description="Пароль пользователя")

class AttendanceResponse(BaseModel):
    message: str
    task_id: Optional[str] = None
    status: str

class AuthResponse(BaseModel):
    message: str
    authenticated: bool
    status: str
    details: Optional[Dict[str, Any]] = None

class LogRequest(BaseModel):
    lines: int = Field(100, description="Количество последних строк для получения")


active_tasks: Dict[str, Dict] = {}
task_lock = threading.Lock()


class BotDebugWrapper:
    
    def __init__(self):
        self.debug_data = {
            "start_time": datetime.now().isoformat(),
            "events": [],
            "errors": [],
            "screenshots": [],
            "html_dumps": []
        }
    
    def log_event(self, event_type: str, message: str, details: dict = None):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message
        }
        if details:
            event["details"] = details
        
        self.debug_data["events"].append(event)
        logger.info(f"[{event_type}] {message}")
    
    def log_error(self, error_type: str, error: Exception, step: str):
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": str(error),
            "step": step,
            "traceback": traceback.format_exc()
        }
        self.debug_data["errors"].append(error_data)
        logger.error(f"[{error_type}] Error in {step}: {error}")
        logger.error(f"Traceback: {error_data['traceback']}")
    
    def log_screenshot(self, name: str, path: str):
        self.debug_data["screenshots"].append({
            "timestamp": datetime.now().isoformat(),
            "name": name,
            "path": path
        })
    
    def save_debug_info(self, task_id: str):
        self.debug_data["end_time"] = datetime.now().isoformat()
        debug_path = os.path.join(logs_dir, f"debug_{task_id}.json")
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(self.debug_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Debug info saved to {debug_path}")
        return debug_path


def run_attendance_bot(task_id: str, username: str, password: str, show_ui: bool):
    debug_wrapper = BotDebugWrapper()
    
    with task_lock:
        active_tasks[task_id]["status"] = "running"
        active_tasks[task_id]["debug_id"] = debug_wrapper.debug_data["start_time"]
    
    try:
        logger.info(f"Starting attendance bot for task {task_id}")
        debug_wrapper.log_event("TASK_START", f"Starting attendance task for {username}")
        
        bot = AttendanceBot(username, password, show_ui)
        
        try:
            debug_wrapper.log_event("SETUP", "Setting up webdriver")
            bot.setup_driver()
            
            bot.driver.implicitly_wait(15)
            
            debug_wrapper.log_event("NAVIGATION", f"Navigating to {BASE_URL}")
            bot.driver.get(BASE_URL)
            
            debug_wrapper.log_event("LOGIN", "Attempting to login")
            login_success = bot.login()
            
            if login_success:
                debug_wrapper.log_event("LOGIN", "Login successful")
                
                debug_wrapper.log_event("WAIT", "Waiting for page to fully load after login")
                time.sleep(3)
                
                debug_wrapper.log_event("ATTENDANCE", "Trying to click attendance buttons")
                try:
                    page_source = bot.driver.page_source
                    has_attendance_btn = "Отметиться" in page_source
                    debug_wrapper.log_event(
                        "PAGE_CHECK", 
                        f"Page contains 'Отметиться': {has_attendance_btn}",
                        {"page_length": len(page_source), "contains_keyword": has_attendance_btn}
                    )
                    
                    if has_attendance_btn:
                        script = """
                        const attendButtons = Array.from(document.querySelectorAll('div[role="button"]'))
                            .filter(el => el.textContent.includes('Отметиться'));
                        
                        const results = [];
                        attendButtons.forEach((btn, idx) => {
                            try {
                                btn.click();
                                results.push({index: idx, success: true});
                            } catch(e) {
                                results.push({index: idx, success: false, error: e.toString()});
                            }
                        });
                        
                        return {
                            total: attendButtons.length,
                            results: results
                        };
                        """
                        js_result = bot.driver.execute_script(script)
                        debug_wrapper.log_event(
                            "JS_CLICK", 
                            f"JavaScript attendance button click results: {js_result['total']} buttons found", 
                            js_result
                        )
                    
                    attendance_count = bot.try_to_attend()
                    debug_wrapper.log_event(
                        "ATTENDANCE", 
                        f"Attempted to mark attendance: {attendance_count} buttons clicked"
                    )
                    
                except Exception as e:
                    debug_wrapper.log_error("ATTENDANCE_ERROR", e, "try_to_attend")
            else:
                debug_wrapper.log_event("LOGIN", "Login failed")
        
        except Exception as e:
            debug_wrapper.log_error("BOT_ERROR", e, "bot_execution")
        
        finally:
            if bot.driver:
                bot.take_screenshot("final_state")
                try:
                    page_content = bot.driver.page_source
                    page_path = os.path.join(logs_dir, f"page_{task_id}.html")
                    with open(page_path, "w", encoding="utf-8") as f:
                        f.write(page_content)
                    debug_wrapper.log_event("PAGE_SAVED", f"Final page saved to {page_path}")
                except Exception as save_err:
                    debug_wrapper.log_error("SAVE_ERROR", save_err, "save_page")
            
            try:
                if bot.driver:
                    bot.cleanup()
                    debug_wrapper.log_event("CLEANUP", "Webdriver closed successfully")
            except Exception as cleanup_err:
                debug_wrapper.log_error("CLEANUP_ERROR", cleanup_err, "driver_cleanup")
        
        with task_lock:
            active_tasks[task_id]["status"] = "completed"
            logger.info(f"Task {task_id} completed successfully")
        
        debug_wrapper.log_event("TASK_COMPLETE", f"Task {task_id} completed")
    
    except Exception as e:
        logger.error(f"Error in task {task_id}: {str(e)}")
        debug_wrapper.log_error("TASK_ERROR", e, "task_execution")
        
        with task_lock:
            active_tasks[task_id]["status"] = "failed"
            active_tasks[task_id]["error"] = str(e)
    
    finally:
        debug_file = debug_wrapper.save_debug_info(task_id)
        with task_lock:
            active_tasks[task_id]["debug_file"] = debug_file


async def check_auth(username: str, password: str) -> tuple[bool, dict]:
    debug_info = {}
    try:
        logger.info(f"Checking authentication for username: {username}")
        bot = AttendanceBot(username, password, show_ui=False)
        
        try:
            logger.debug("Setting up webdriver for auth check")
            bot.setup_driver()
            debug_info["driver_setup"] = "success"
            
            logger.debug(f"Navigating to {BASE_URL}")
            bot.driver.get(BASE_URL)
            debug_info["navigation"] = "success"
            
            logger.debug("Attempting to login")
            auth_success = bot.login()
            debug_info["login_attempt"] = "success"
            debug_info["login_result"] = auth_success
            
            if auth_success and bot.driver:
                try:
                    page_title = bot.driver.title
                    debug_info["page_title"] = page_title
                    
                    has_menu = len(bot.driver.find_elements("xpath", "//div[contains(@class, 'v-menubar')]")) > 0
                    debug_info["has_menu"] = has_menu
                    
                    has_classes = "Дисциплины" in bot.driver.page_source
                    debug_info["has_classes"] = has_classes
                    
                    has_attend_btn = "Отметиться" in bot.driver.page_source
                    debug_info["has_attend_btn"] = has_attend_btn
                except Exception as page_err:
                    debug_info["page_check_error"] = str(page_err)
            
            logger.info(f"Authentication check result: {auth_success}")
            return auth_success, debug_info
        
        except Exception as e:
            logger.error(f"Error during webdriver operations: {e}")
            debug_info["webdriver_error"] = str(e)
            debug_info["traceback"] = traceback.format_exc()
            return False, debug_info
        
        finally:
            try:
                if hasattr(bot, 'driver') and bot.driver:
                    logger.debug("Cleaning up webdriver")
                    bot.cleanup()
                    debug_info["cleanup"] = "success"
            except Exception as cleanup_err:
                logger.error(f"Error during cleanup: {cleanup_err}")
                debug_info["cleanup_error"] = str(cleanup_err)
    
    except Exception as e:
        logger.error(f"Error during authentication check: {e}")
        debug_info["error"] = str(e)
        debug_info["traceback"] = traceback.format_exc()
        return False, debug_info


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.debug(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.debug(f"Response: status={response.status_code}, time={process_time:.3f}s")
        return response
    except Exception as e:
        logger.error(f"Request error: {e}")
        raise


@app.get("/", response_model=AttendanceResponse)
async def root():
    return {"message": "Attendance Bot API is running", "status": "active"}


@app.get("/logs", response_class=FileResponse)
async def get_logs(lines: int = 100):
    try:
        return FileResponse(
            path=log_filename,
            filename=os.path.basename(log_filename),
            media_type="text/plain"
        )
    except Exception as e:
        logger.error(f"Error serving logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get logs: {str(e)}"
        )


@app.get("/auth/env-check", response_model=AuthResponse)
async def check_env_authentication():
    try:
        if not USERNAME or not PASSWORD:
            logger.warning("Missing credentials in .env file")
            return {
                "message": "Отсутствуют учетные данные в .env файле",
                "authenticated": False,
                "status": "error",
                "details": {"username_present": bool(USERNAME), "password_present": bool(PASSWORD)}
            }
            
        logger.info("Checking authentication with credentials from .env")
        is_authenticated, debug_info = await check_auth(USERNAME, PASSWORD)
        
        if is_authenticated:
            logger.info("Authentication with .env credentials was successful")
            return {
                "message": "Авторизация с данными из .env выполнена успешно",
                "authenticated": True,
                "status": "success",
                "details": debug_info
            }
        else:
            logger.warning("Authentication with .env credentials failed")
            return {
                "message": "Не удалось авторизоваться с данными из .env. Проверьте логин и пароль",
                "authenticated": False,
                "status": "failed",
                "details": debug_info
            }
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error during .env authentication check: {e}")
        logger.error(f"Error details: {error_details}")
        return {
            "message": f"Ошибка при проверке авторизации с данными из .env: {str(e)}",
            "authenticated": False,
            "status": "error",
            "details": {"error": str(e), "traceback": error_details}
        }


@app.post("/auth/check", response_model=AuthResponse)
async def check_authentication(data: AuthCheckRequest):
    try:
        logger.info(f"Checking authentication for user: {data.username}")
        is_authenticated, debug_info = await check_auth(data.username, data.password)
        
        if is_authenticated:
            return {
                "message": "Авторизация выполнена успешно",
                "authenticated": True,
                "status": "success",
                "details": debug_info
            }
        else:
            return {
                "message": "Не удалось авторизоваться. Проверьте логин и пароль",
                "authenticated": False,
                "status": "failed",
                "details": debug_info
            }
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error checking authentication: {e}")
        logger.error(f"Error details: {error_details}")
        return {
            "message": f"Ошибка при проверке авторизации: {str(e)}",
            "authenticated": False,
            "status": "error",
            "details": {"error": str(e), "traceback": error_details}
        }


@app.post("/attend", response_model=AttendanceResponse)
async def attend(data: AttendanceRequest, background_tasks: BackgroundTasks):
    try:
        task_id = f"task_{len(active_tasks) + 1}_{int(time.time())}"
        logger.info(f"Creating new attendance task: {task_id} for user {data.username}")
        
        with task_lock:
            active_tasks[task_id] = {
                "username": data.username,
                "created_at": time.time(),
                "status": "pending",
                "show_ui": data.show_ui
            }
        
        background_tasks.add_task(
            run_attendance_bot, 
            task_id=task_id,
            username=data.username,
            password=data.password,
            show_ui=data.show_ui
        )
        
        return {
            "message": "Attendance bot started in background",
            "task_id": task_id,
            "status": "pending"
        }
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error starting attendance bot: {e}")
        logger.error(f"Error details: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start attendance bot: {str(e)}"
        )


@app.get("/task/{task_id}", response_model=AttendanceResponse)
async def get_task_status(task_id: str):
    with task_lock:
        if task_id not in active_tasks:
            logger.warning(f"Task {task_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        task_info = active_tasks[task_id]
        
        response = {
            "message": f"Task status: {task_info['status']}",
            "task_id": task_id,
            "status": task_info['status']
        }
        
        if "error" in task_info:
            response["message"] += f" (Error: {task_info['error']})"
            
        return response


@app.get("/task/{task_id}/debug")
async def get_task_debug(task_id: str):
    with task_lock:
        if task_id not in active_tasks:
            logger.warning(f"Task {task_id} not found for debug info")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        task_info = active_tasks[task_id]
        
        if "debug_file" in task_info and os.path.exists(task_info["debug_file"]):
            try:
                with open(task_info["debug_file"], "r", encoding="utf-8") as f:
                    debug_data = json.load(f)
                return debug_data
            except Exception as e:
                logger.error(f"Error reading debug file: {e}")
                return {"error": f"Failed to read debug info: {str(e)}"}
        
        return {
            "task_id": task_id,
            "status": task_info["status"],
            "created_at": task_info["created_at"],
            "username": task_info["username"],
            "show_ui": task_info.get("show_ui", False),
            "error": task_info.get("error", None),
            "note": "Detailed debug information not available for this task"
        }


@app.get("/tasks", response_model=Dict[str, dict])
async def list_tasks():
    """Возвращает список всех задач"""
    with task_lock:
        return active_tasks


@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """Удаляет задачу по ID"""
    with task_lock:
        if task_id not in active_tasks:
            logger.warning(f"Task {task_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        if active_tasks[task_id]["status"] not in ["completed", "failed"]:
            logger.warning(f"Cannot delete active task {task_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete active task. Current status: {active_tasks[task_id]['status']}"
            )
            
        del active_tasks[task_id]
        logger.info(f"Task {task_id} deleted successfully")
        
    return JSONResponse(
        content={"message": f"Task {task_id} deleted successfully"},
        status_code=status.HTTP_200_OK
    )


@app.on_event("startup")
async def startup_event():
    logger.info("=== Attendance Bot API started ===")
    logger.info(f"Environment: USERNAME={'present' if USERNAME else 'missing'}, BASE_URL={BASE_URL}")
    logger.info(f"Log file: {log_filename}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("=== Attendance Bot API shutting down ===")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))