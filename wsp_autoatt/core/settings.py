import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    update_interval: int = 40
    wait_time: int = 10
    show_ui: bool = False
    chrome_binary_path: str = "/usr/bin/chromium"
    chromedriver_path: str = "/usr/bin/chromedriver"
    chrome_sessions_dir: str = "chrome_sessions"
    wsp_username: str = ""
    wsp_password: str = ""
    api_base_url: str = "http://localhost:8000"


# Keep environment parsing centralized to avoid magic constants across modules.
def get_settings() -> Settings:
    return Settings(
        update_interval=int(os.getenv("UPDATE_INTERVAL", "40")),
        wait_time=int(os.getenv("WAIT_TIME", "10")),
        show_ui=os.getenv("SHOW_UI", "false").lower() in {"1", "true", "yes", "on"},
        chrome_binary_path=os.getenv("CHROME_BINARY_PATH", "/usr/bin/chromium"),
        chromedriver_path=os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"),
        chrome_sessions_dir=os.getenv("CHROME_SESSIONS_DIR", "chrome_sessions"),
        wsp_username=os.getenv("WSP_USERNAME", ""),
        wsp_password=os.getenv("WSP_PASSWORD", ""),
        api_base_url=os.getenv("API_BASE_URL", "http://localhost:8000"),
    )
