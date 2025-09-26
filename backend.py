import uvicorn
import asyncio
import threading
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from main import attend_bot

app = FastAPI()

# Статус бота
bot_status = {
    "running": False, 
    "message": "Bot not started", 
    "last_error": None,
    "subjects_found": False,
    "last_attendance_check": None,
    "attendance_marked": False
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_bot_in_background(username: str, password: str):
    """Запускает бота в отдельном потоке"""
    global bot_status
    try:
        bot_status["running"] = True
        bot_status["message"] = f"Bot started for user {username}"
        bot_status["last_error"] = None
        attend_bot(username, password)
    except Exception as e:
        bot_status["running"] = False
        bot_status["last_error"] = str(e)
        bot_status["message"] = f"Bot stopped with error: {str(e)}"


@app.get("/")
async def root():
    return {"message": "Attendance Bot API"}


@app.get("/attend")
async def attend(username: str, password: str, background_tasks: BackgroundTasks):
    """Запускает бота в фоновом режиме"""
    if bot_status["running"]:
        return {"message": "Bot is already running", "status": bot_status}
    
    # Запускаем бота в фоновом потоке
    thread = threading.Thread(target=run_bot_in_background, args=(username, password))
    thread.daemon = True
    thread.start()
    
    return {"message": f"Bot started for user {username}", "status": "started"}


@app.get("/status")
async def get_status():
    """Получить статус бота"""
    return bot_status


@app.get("/stop")
async def stop_bot():
    """Остановить бота (пока что только обновляет статус)"""
    global bot_status
    bot_status["running"] = False
    bot_status["message"] = "Bot stopped by user request"
    return {"message": "Stop signal sent", "status": bot_status}


@app.get("/logs")
async def get_logs():
    """Получить логи Docker контейнера"""
    import subprocess
    try:
        # Получаем последние 50 строк логов
        result = subprocess.run(
            ["docker", "logs", "--tail", "50", "wsp-autoatt-wsp-autoattend-1"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logs = result.stdout + result.stderr
            return {"logs": logs.split('\n'), "status": "success"}
        else:
            return {"logs": ["Error getting logs"], "status": "error", "error": result.stderr}
    except Exception as e:
        return {"logs": [f"Error: {str(e)}"], "status": "error"}


@app.get("/check-page")
async def check_page_content(url: str = "https://wsp.kbtu.kz/StudentSchedule"):
    """Проверить содержимое страницы с авторизацией"""
    from main import check_specific_page
    try:
        result = check_specific_page(url)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/notifications")
async def get_notifications():
    """Получить уведомления для Telegram бота"""
    global bot_status
    
    notifications = []
    
    # Проверяем новые события
    if bot_status.get("subjects_found") and not bot_status.get("attendance_marked"):
        notifications.append({
            "type": "subjects_available",
            "message": "🎯 Найдены предметы для отметки посещения!",
            "timestamp": bot_status.get("last_attendance_check")
        })
    
    if bot_status.get("attendance_marked"):
        notifications.append({
            "type": "attendance_marked", 
            "message": "✅ Посещение отмечено успешно!",
            "timestamp": bot_status.get("last_attendance_check")
        })
        # Сбрасываем флаг после отправки уведомления
        bot_status["attendance_marked"] = False
    
    if bot_status.get("last_error"):
        notifications.append({
            "type": "error",
            "message": f"❌ Ошибка: {bot_status['last_error']}",
            "timestamp": datetime.now().isoformat()
        })
    
    return {"notifications": notifications, "count": len(notifications)}


@app.post("/webhook/attendance-update")
async def attendance_webhook(data: dict):
    """Webhook для получения обновлений от attendance bot"""
    global bot_status
    
    if data.get("type") == "subjects_found":
        bot_status["subjects_found"] = True
        bot_status["last_attendance_check"] = datetime.now().isoformat()
    elif data.get("type") == "attendance_marked":
        bot_status["attendance_marked"] = True
        bot_status["subjects_found"] = False
        bot_status["last_attendance_check"] = datetime.now().isoformat()
    
    return {"status": "received"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)