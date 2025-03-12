import logging
import os
import threading
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from main import attend_bot

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api.log"),
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

class AttendanceResponse(BaseModel):
    message: str
    task_id: Optional[str] = None
    status: str


active_tasks: Dict[str, Dict] = {}
task_lock = threading.Lock()


def run_attendance_bot(task_id: str, username: str, password: str, show_ui: bool):
    with task_lock:
        active_tasks[task_id]["status"] = "running"
    
    try:
        logger.info(f"Starting attendance bot for task {task_id}")
        attend_bot(username, password, show_ui)
        with task_lock:
            active_tasks[task_id]["status"] = "completed"
            logger.info(f"Task {task_id} completed successfully")
    except Exception as e:
        logger.error(f"Error in task {task_id}: {str(e)}")
        with task_lock:
            active_tasks[task_id]["status"] = "failed"
            active_tasks[task_id]["error"] = str(e)


@app.get("/", response_model=AttendanceResponse)
async def root():
    return {"message": "Attendance Bot API is running", "status": "active"}


@app.post("/attend", response_model=AttendanceResponse)
async def attend(data: AttendanceRequest, background_tasks: BackgroundTasks):
    try:
        task_id = f"task_{len(active_tasks) + 1}_{int(time.time())}"
        
        with task_lock:
            active_tasks[task_id] = {
                "username": data.username,
                "created_at": time.time(),
                "status": "pending"
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
        logger.error(f"Error starting attendance bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start attendance bot: {str(e)}"
        )


@app.get("/task/{task_id}", response_model=AttendanceResponse)
async def get_task_status(task_id: str):
    with task_lock:
        if task_id not in active_tasks:
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


@app.get("/tasks", response_model=Dict[str, dict])
async def list_tasks():
    with task_lock:
        return active_tasks


@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    with task_lock:
        if task_id not in active_tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        if active_tasks[task_id]["status"] not in ["completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete active task. Current status: {active_tasks[task_id]['status']}"
            )
            
        del active_tasks[task_id]
        
    return JSONResponse(
        content={"message": f"Task {task_id} deleted successfully"},
        status_code=status.HTTP_200_OK
    )


@app.on_event("startup")
async def startup_event():
    logger.info("Attendance Bot API started")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Attendance Bot API shutting down")


if __name__ == "__main__":
    import time
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))