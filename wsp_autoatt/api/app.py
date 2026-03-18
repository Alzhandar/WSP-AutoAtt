import subprocess

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wsp_autoatt.bot.attendance import check_specific_page, run_debug_session
from wsp_autoatt.bot.manager import bot_manager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Attendance Bot API",
        "service": "wsp_autoatt",
        "status": bot_manager.status(),
    }


@app.get("/attend")
async def attend(username: str, password: str):
    """Запускает бота в фоновом режиме"""
    return bot_manager.start(username, password)


@app.get("/status")
async def get_status():
    """Получить статус бота"""
    return bot_manager.status()


@app.get("/stop")
async def stop_bot():
    """Остановить бота (soft stop request)"""
    return bot_manager.stop()


@app.get("/logs")
async def get_logs():
    """Получить логи Docker контейнера"""
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
    try:
        result = check_specific_page(url)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/debug-session")
async def debug_session(username: str, password: str):
    """Запустить отладочную сессию для диагностики проблем"""
    try:
        result = run_debug_session(username, password)
        return {"status": "success", "data": result}
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)