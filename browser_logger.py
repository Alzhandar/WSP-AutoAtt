import sys
import time
import logging
import json
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.syntax import Syntax
from rich.box import ROUNDED
from rich.style import Style
from rich.logging import RichHandler


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)

logger = logging.getLogger("browser_monitor")

# Rich консоль для красивого вывода
console = Console(highlight=True)


@dataclass
class PageState:
    """Хранение информации о состоянии страницы."""
    title: str = ""
    url: str = ""
    elements_count: int = 0
    visible_text: str = ""
    important_elements: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    current_form_data: Dict[str, str] = field(default_factory=dict)
    last_update: float = 0
    logs: List[Dict[str, Any]] = field(default_factory=list)


class BrowserMonitor:
    """Класс для мониторинга и визуализации состояния браузера в терминале."""
    
    def __init__(self, 
                 update_interval: float = 1.0, 
                 max_logs: int = 50,
                 screenshots_dir: Optional[Path] = None):
        """
        Инициализация монитора состояния браузера.
        
        Args:
            update_interval: Интервал обновления состояния в секундах.
            max_logs: Максимальное количество записей лога для хранения.
            screenshots_dir: Директория для сохранения скриншотов.
        """
        self.update_interval = update_interval
        self.max_logs = max_logs
        self.screenshots_dir = screenshots_dir or Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        
        self.state = PageState()
        self.previous_state = None
        self.important_elements_patterns = {
            "buttons": ["button", "div[@role='button']", "a[contains(@class, 'btn')]"],
            "forms": ["form", "div[contains(@class, 'form')]"],
            "inputs": ["input", "textarea", "select"],
            "tables": ["table", "div[contains(@class, 'table')]"],
            "alerts": ["div[contains(@class, 'alert')]", "div[contains(@class, 'notification')]"],
        }
        
        # Регулярные выражения для идентификации ключевых элементов интерфейса
        self.key_patterns = {
            "login": r"(?i)(вход|логин|sign\s*in|log\s*in|авторизац)",
            "attendance": r"(?i)(отметиться|посещаемость|attendance|presence|присутств)",
            "error": r"(?i)(ошибка|error|fail|неудач|некорректн)",
            "success": r"(?i)(успешно|success|выполнен)"
        }
    
    def update_state(self, driver: WebDriver) -> None:
        """
        Обновляет состояние страницы на основе текущего состояния браузера.
        
        Args:
            driver: Экземпляр Selenium WebDriver.
        """
        now = time.time()
        if now - self.state.last_update < self.update_interval:
            return
            
        # Сохраняем предыдущее состояние для сравнения
        self.previous_state = PageState(**{
            "title": self.state.title,
            "url": self.state.url,
            "elements_count": self.state.elements_count,
            "visible_text": self.state.visible_text,
            "important_elements": self.state.important_elements.copy(),
            "alerts": self.state.alerts.copy(),
            "current_form_data": self.state.current_form_data.copy(),
            "last_update": self.state.last_update,
            "logs": self.state.logs.copy()
        })
        
        try:
            # Основная информация о странице
            self.state.title = driver.title
            self.state.url = driver.current_url
            
            # Анализ HTML с помощью BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")
            self.state.elements_count = len(soup.find_all())
            
            # Извлечение видимого текста с обработкой
            visible_text = soup.get_text(separator=' ', strip=True)
            visible_text = ' '.join(visible_text.split())  # Нормализация пробелов
            if len(visible_text) > 500:
                visible_text = visible_text[:500] + "..."
            self.state.visible_text = visible_text
            
            # Получение информации о важных элементах страницы
            self.collect_important_elements(driver)
            
            # Проверка наличия алертов и уведомлений
            alerts = self.extract_alerts(driver)
            if alerts != self.state.alerts:
                self.state.alerts = alerts
                for alert in alerts:
                    self.log_event("alert", f"Обнаружено уведомление: {alert}")
            
            # Сбор данных формы, если есть
            self.state.current_form_data = self.extract_form_data(driver)
            
            # Обновление времени последнего обновления
            self.state.last_update = now
            
            # Анализ изменений состояния
            self.analyze_state_changes()
            
        except Exception as e:
            logger.exception(f"Ошибка при обновлении состояния страницы: {e}")
            self.log_event("error", f"Ошибка мониторинга: {str(e)}")
    
    def collect_important_elements(self, driver: WebDriver) -> None:
        """
        Собирает информацию о важных элементах пользовательского интерфейса.
        
        Args:
            driver: Экземпляр Selenium WebDriver.
        """
        important_elements = {}
        
        try:
            for element_type, xpaths in self.important_elements_patterns.items():
                elements = []
                for xpath_pattern in xpaths:
                    try:
                        found_elements = driver.find_elements("xpath", f"//{xpath_pattern}")
                        for element in found_elements:
                            try:
                                if not element.is_displayed():
                                    continue
                                    
                                element_info = {
                                    "text": (element.text or "").strip(),
                                    "tag": element.tag_name,
                                    "classes": (element.get_attribute("class") or "").strip(),
                                    "id": (element.get_attribute("id") or "").strip(),
                                    "type": (element.get_attribute("type") or "").strip(),
                                    "name": (element.get_attribute("name") or "").strip(),
                                    "value": (element.get_attribute("value") or "").strip(),
                                    "is_enabled": element.is_enabled(),
                                }
                                
                                # Если это поле для ввода пароля, скрываем значение
                                if element_info["type"] == "password" and element_info["value"]:
                                    element_info["value"] = "********"
                                    
                                # Выявление ключевых элементов по паттернам
                                element_info["key_element"] = self.is_key_element(element_info)
                                
                                elements.append(element_info)
                            except:
                                continue
                    except:
                        continue
                        
                if elements:
                    important_elements[element_type] = elements
                    
            self.state.important_elements = important_elements
            
        except Exception as e:
            logger.exception(f"Ошибка при сборе важных элементов: {e}")
    
    def is_key_element(self, element_info: Dict[str, Any]) -> str:
        """
        Определяет, является ли элемент ключевым элементом интерфейса.
        
        Args:
            element_info: Информация об элементе.
            
        Returns:
            Строка с типом ключевого элемента или пустая строка.
        """
        text = f"{element_info['text']} {element_info['name']} {element_info['id']} {element_info['classes']}"
        
        for key, pattern in self.key_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return key
                
        return ""
    
    def extract_alerts(self, driver: WebDriver) -> List[str]:
        """
        Извлекает текст алертов и уведомлений со страницы.
        
        Args:
            driver: Экземпляр Selenium WebDriver.
            
        Returns:
            Список строк с текстами алертов.
        """
        alerts = []
        
        # Проверка js-алертов
        try:
            alert = driver.switch_to.alert
            alerts.append(f"JS Alert: {alert.text}")
            # Не закрываем алерт здесь, так как это может быть частью функциональности
        except:
            pass
            
        # Поиск алертов в DOM
        alert_classes = [
            "alert", "notification", "toast", "message", 
            "error", "success", "info", "warning"
        ]
        
        for cls in alert_classes:
            try:
                elements = driver.find_elements("css selector", f".{cls}")
                for element in elements:
                    if element.is_displayed() and element.text.strip():
                        alerts.append(element.text.strip())
            except:
                continue
                
        return alerts
    
    def extract_form_data(self, driver: WebDriver) -> Dict[str, str]:
        """
        Извлекает данные из форм на странице.
        
        Args:
            driver: Экземпляр Selenium WebDriver.
            
        Returns:
            Словарь с данными формы.
        """
        form_data = {}
        try:
            input_elements = driver.find_elements("xpath", "//input | //textarea | //select")
            for element in input_elements:
                try:
                    if not element.is_displayed():
                        continue
                        
                    name = element.get_attribute("name") or element.get_attribute("id") or ""
                    if not name:
                        continue
                        
                    element_type = element.get_attribute("type") or ""
                    value = element.get_attribute("value") or ""
                    
                    if element_type == "password":
                        value = "********" if value else ""
                        
                    if element_type == "checkbox" or element_type == "radio":
                        value = "checked" if element.is_selected() else "unchecked"
                        
                    form_data[name] = value
                except:
                    continue
        except Exception as e:
            logger.exception(f"Ошибка при извлечении данных формы: {e}")
            
        return form_data
    
    def analyze_state_changes(self) -> None:
        """Анализирует изменения состояния страницы между обновлениями."""
        if not self.previous_state:
            return
            
        # Изменение URL
        if self.state.url != self.previous_state.url:
            self.log_event("navigation", f"Переход на: {self.state.url}")
            
        # Изменение заголовка
        if self.state.title != self.previous_state.title:
            self.log_event("page_changed", f"Новый заголовок: {self.state.title}")
            
        # Значительное изменение контента
        if self.previous_state.elements_count > 0:
            change_ratio = abs(self.state.elements_count - self.previous_state.elements_count) / self.previous_state.elements_count
            if change_ratio > 0.3:  # Если изменилось более 30% элементов
                self.log_event("content_changed", f"Значительное изменение контента страницы: {self.state.elements_count} элементов")
        
        # Проверка появления ключевых элементов интерфейса
        self.check_important_elements_changes()
    
    def check_important_elements_changes(self) -> None:
        """Проверяет изменения в важных элементах пользовательского интерфейса."""
        # Поиск новых элементов с ключевыми паттернами
        for element_type, elements in self.state.important_elements.items():
            for element in elements:
                if element["key_element"] and self._is_new_key_element(element_type, element):
                    self.log_event(
                        "ui_element", 
                        f"Обнаружен ключевой элемент: [{element['key_element']}] {element['text'] or element['name'] or element['id']}"
                    )
    
    def _is_new_key_element(self, element_type: str, element: Dict[str, Any]) -> bool:
        """
        Проверяет, является ли элемент новым ключевым элементом.
        
        Args:
            element_type: Тип элемента (кнопка, форма и т.д.)
            element: Информация об элементе
            
        Returns:
            True, если это новый ключевой элемент
        """
        if not self.previous_state or element_type not in self.previous_state.important_elements:
            return True
            
        # Формируем идентификатор элемента для сравнения
        element_id = f"{element['id']}_{element['name']}_{element['text']}"
        
        for prev_element in self.previous_state.important_elements.get(element_type, []):
            prev_id = f"{prev_element['id']}_{prev_element['name']}_{prev_element['text']}"
            if prev_id == element_id and prev_element.get("key_element") == element["key_element"]:
                return False
                
        return True
    
    def log_event(self, event_type: str, message: str, details: Dict[str, Any] = None) -> None:
        """
        Добавляет событие в лог состояния.
        
        Args:
            event_type: Тип события
            message: Сообщение события
            details: Дополнительные детали (опционально)
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message
        }
        
        if details:
            event["details"] = details
            
        self.state.logs.append(event)
        
        # Ограничение размера лога
        if len(self.state.logs) > self.max_logs:
            self.state.logs = self.state.logs[-self.max_logs:]
            
        # Логирование для отладки
        log_color = self._get_log_color(event_type)
        logger.info(f"[{log_color}]{event_type}[/{log_color}]: {message}")
    
    def _get_log_color(self, event_type: str) -> str:
        """Возвращает цвет для типа события лога."""
        colors = {
            "navigation": "blue",
            "page_changed": "cyan",
            "content_changed": "cyan",
            "ui_element": "green",
            "alert": "yellow",
            "error": "red",
            "action": "magenta"
        }
        return colors.get(event_type, "white")
    
    def display_current_state(self) -> None:
        """Отображает текущее состояние страницы в консоли."""
        console.clear()
        
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        
        layout["main"].split_row(
            Layout(name="main_info", ratio=2),
            Layout(name="sidebar", ratio=1),
        )
        
        layout["main_info"].split(
            Layout(name="page_info"),
            Layout(name="elements"),
            Layout(name="form_data"),
        )
        
        layout["sidebar"].split(
            Layout(name="alerts"),
            Layout(name="logs"),
        )
        
        # Заголовок
        header = Table.grid()
        header.add_row(
            Panel(
                Text(f"WSP Browser Monitor - {self.state.title}", style="bold white on blue"),
                border_style="blue"
            )
        )
        layout["header"].update(header)
        
        # Основная информация о странице
        page_info = Table.grid()
        page_info.add_row(Panel(
            "\n".join([
                f"[bold]URL:[/bold] {self.state.url}",
                f"[bold]Title:[/bold] {self.state.title}",
                f"[bold]Elements:[/bold] {self.state.elements_count}",
                f"[bold]Updated:[/bold] {datetime.fromtimestamp(self.state.last_update).strftime('%H:%M:%S')}",
                "",
                f"[bold]Visible Text:[/bold]",
                Text(self.state.visible_text, style="dim white"),
            ]),
            title="Информация о странице",
            border_style="cyan",
            box=ROUNDED
        ))
        layout["page_info"].update(page_info)
        
        # Важные элементы страницы
        elements_table = Table.grid()
        elements_content = []
        
        for element_type, elements in self.state.important_elements.items():
            if not elements:
                continue
                
            elements_content.append(f"[bold]{element_type.capitalize()}:[/bold]")
            
            for i, element in enumerate(elements[:5]):  # Ограничиваем вывод до 5 элементов
                key_mark = f"[{element['key_element']}] " if element["key_element"] else ""
                element_text = element["text"] or element["value"] or element["name"] or element["id"]
                if not element_text:
                    continue
                    
                # Сокращаем слишком длинный текст
                if len(element_text) > 50:
                    element_text = element_text[:47] + "..."
                
                style = "green" if element["is_enabled"] else "dim"
                elements_content.append(f"  {i+1}. {key_mark}[{style}]{element_text}[/{style}]")
            
            if len(elements) > 5:
                elements_content.append(f"  ... и ещё {len(elements) - 5}")
            
            elements_content.append("")
            
        if not elements_content:
            elements_content = ["Нет важных элементов на странице"]
            
        elements_table.add_row(Panel(
            "\n".join(elements_content),
            title="Ключевые элементы интерфейса",
            border_style="green",
            box=ROUNDED
        ))
        layout["elements"].update(elements_table)
        
        # Данные форм
        form_table = Table.grid()
        form_content = []
        
        for name, value in self.state.current_form_data.items():
            form_content.append(f"[bold]{name}:[/bold] {value}")
            
        if not form_content:
            form_content = ["Нет данных форм"]
            
        form_table.add_row(Panel(
            "\n".join(form_content),
            title="Данные форм",
            border_style="blue",
            box=ROUNDED
        ))
        layout["form_data"].update(form_table)
        
        # Алерты и уведомления
        alerts_table = Table.grid()
        alerts_content = []
        
        for alert in self.state.alerts:
            alerts_content.append(f"• {alert}")
            
        if not alerts_content:
            alerts_content = ["Нет уведомлений"]
            
        alerts_table.add_row(Panel(
            "\n".join(alerts_content),
            title="Уведомления",
            border_style="yellow",
            box=ROUNDED
        ))
        layout["alerts"].update(alerts_table)
        
        # Логи событий
        logs_table = Table.grid()
        logs_content = []
        
        for log in reversed(self.state.logs[-10:]):  # Последние 10 событий
            timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%H:%M:%S")
            log_type = log["type"]
            color = self._get_log_color(log_type)
            logs_content.append(f"[dim]{timestamp}[/dim] [{color}]{log_type}[/{color}] {log['message']}")
            
        if not logs_content:
            logs_content = ["Нет событий"]
            
        logs_table.add_row(Panel(
            "\n".join(logs_content),
            title="Журнал событий",
            border_style="magenta",
            box=ROUNDED
        ))
        layout["logs"].update(logs_table)
        
        # Нижний колонтитул
        footer = Table.grid()
        footer.add_row(
            Panel(
                Text("Нажмите [Ctrl+C] для завершения.", style="dim"),
                border_style="dim"
            )
        )
        layout["footer"].update(footer)
        
        console.print(layout)
    
    def take_screenshot(self, driver: WebDriver, name: str) -> Optional[str]:
        """
        Создает скриншот текущего состояния страницы.
        
        Args:
            driver: Экземпляр Selenium WebDriver.
            name: Название скриншота.
            
        Returns:
            Путь к сохраненному скриншоту или None в случае ошибки.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name.replace(' ', '_')}.png"
            filepath = self.screenshots_dir / filename
            
            driver.save_screenshot(str(filepath))
            self.log_event("screenshot", f"Сохранен скриншот: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.exception(f"Ошибка при создании скриншота '{name}': {e}")
            return None


# Функция для интеграции с AttendanceBot
def integrate_browser_monitor(attendance_bot):
    """
    Интегрирует мониторинг браузера с классом AttendanceBot.
    
    Args:
        attendance_bot: Экземпляр класса AttendanceBot.
    """
    # Создание монитора
    monitor = BrowserMonitor(
        update_interval=0.5,
        screenshots_dir=Path("screenshots")
    )
    
    # Оригинальные методы класса
    original_setup = attendance_bot.setup_driver
    original_login = attendance_bot.login
    original_try_to_attend = attendance_bot.try_to_attend
    original_run = attendance_bot.run
    original_cleanup = attendance_bot.cleanup
    
    # Обертки для методов
    def wrapped_setup_driver(*args, **kwargs):
        result = original_setup(*args, **kwargs)
        monitor.log_event("setup", "Инициализация веб-драйвера завершена")
        if attendance_bot.driver:
            monitor.update_state(attendance_bot.driver)
            monitor.display_current_state()
        return result
        
    def wrapped_login(*args, **kwargs):
        monitor.log_event("action", "Попытка авторизации")
        if attendance_bot.driver:
            monitor.update_state(attendance_bot.driver)
            monitor.display_current_state()
            monitor.take_screenshot(attendance_bot.driver, "before_login")
            
        result = original_login(*args, **kwargs)
        
        if attendance_bot.driver:
            monitor.update_state(attendance_bot.driver)
            monitor.log_event("result", f"Авторизация: {'успешно' if result else 'неудача'}")
            monitor.display_current_state()
            monitor.take_screenshot(attendance_bot.driver, "after_login")
            
        return result
        
    def wrapped_try_to_attend(*args, **kwargs):
        monitor.log_event("action", "Попытка отметить посещаемость")
        if attendance_bot.driver:
            monitor.update_state(attendance_bot.driver)
            monitor.display_current_state()
            monitor.take_screenshot(attendance_bot.driver, "before_attendance")
            
        result = original_try_to_attend(*args, **kwargs)
        
        if attendance_bot.driver:
            monitor.update_state(attendance_bot.driver)
            monitor.log_event("result", f"Отмечено посещений: {result}")
            monitor.display_current_state()
            monitor.take_screenshot(attendance_bot.driver, "after_attendance")
            
        return result
        
    def wrapped_run(*args, **kwargs):
        monitor.log_event("action", "Запуск основного цикла бота")
        
        try:
            result = original_run(*args, **kwargs)
            return result
        except Exception as e:
            monitor.log_event("error", f"Ошибка в основном цикле: {str(e)}")
            raise
        finally:
            if attendance_bot.driver:
                monitor.update_state(attendance_bot.driver)
                monitor.display_current_state()
                
    def wrapped_cleanup(*args, **kwargs):
        monitor.log_event("action", "Завершение работы и очистка ресурсов")
        result = original_cleanup(*args, **kwargs)
        return result
    
    attendance_bot.setup_driver = wrapped_setup_driver
    attendance_bot.login = wrapped_login
    attendance_bot.try_to_attend = wrapped_try_to_attend
    attendance_bot.run = wrapped_run
    attendance_bot.cleanup = wrapped_cleanup
    
    def update_display(*args, **kwargs):
        if attendance_bot.driver:
            monitor.update_state(attendance_bot.driver)
            monitor.display_current_state()
    
    attendance_bot.update_display = update_display
    
    def toggle_display_mode():
        nonlocal monitor
        monitor.update_interval = 2.0 if monitor.update_interval == 0.5 else 0.5
        monitor.log_event("system", f"Интервал обновления изменен на {monitor.update_interval} сек.")
    
    attendance_bot.toggle_display_mode = toggle_display_mode
    
    return monitor


if __name__ == "__main__":
    from main import AttendanceBot, USERNAME, PASSWORD
    
    bot = AttendanceBot(USERNAME, PASSWORD, show_ui=False)
    monitor = integrate_browser_monitor(bot)
    
    try:
        bot.setup_driver()
        bot.run()
    except KeyboardInterrupt:
        console.print("[bold yellow]Прервано пользователем[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Ошибка: {str(e)}[/bold red]")
    finally:
        bot.cleanup()