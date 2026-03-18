from dataclasses import asdict, dataclass
from threading import Lock, Thread
from typing import Any, Dict, Optional

from wsp_autoatt.bot.attendance import UserBlockedError, attend_bot


@dataclass
class BotStatus:
    running: bool = False
    stop_requested: bool = False
    message: str = "Bot not started"
    last_error: Optional[str] = None
    active_username: Optional[str] = None


class BotManager:
    def __init__(self) -> None:
        self._status = BotStatus()
        self._lock = Lock()

    def _set_status(self, **kwargs: Any) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self._status, key, value)

    def _run_worker(self, username: str, password: str) -> None:
        self._set_status(
            running=True,
            stop_requested=False,
            message=f"Bot started for user {username}",
            last_error=None,
            active_username=username,
        )
        try:
            attend_bot(username, password)
            self._set_status(running=False, message="Bot finished", active_username=None)
        except UserBlockedError as exc:
            self._set_status(
                running=False,
                last_error=str(exc),
                message="Bot stopped: user blocked by WSP restrictions",
                active_username=None,
            )
        except Exception as exc:
            self._set_status(
                running=False,
                last_error=str(exc),
                message=f"Bot stopped with error: {exc}",
                active_username=None,
            )

    def start(self, username: str, password: str) -> Dict[str, Any]:
        with self._lock:
            if self._status.running:
                return {"ok": False, "message": "Bot is already running", "status": asdict(self._status)}

        thread = Thread(target=self._run_worker, args=(username, password), daemon=True)
        thread.start()
        return {"ok": True, "message": f"Bot started for user {username}", "status": asdict(self._status)}

    def stop(self) -> Dict[str, Any]:
        self._set_status(stop_requested=True, message="Stop requested by user")
        return {"ok": True, "message": "Stop request accepted", "status": asdict(self._status)}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return asdict(self._status)


bot_manager = BotManager()
