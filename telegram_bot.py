import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8375288159:AAGlk5QRly4f70B0bTK4_pTEYeVAzTx02ho")
ATTENDANCE_API_URL = os.getenv("ATTENDANCE_API_URL", "http://localhost:8000")
ADMIN_USER_ID = None  # Будет установлен при первом запуске

# Хранилище данных пользователей
user_data: Dict[int, Dict] = {}
last_attendance_status = {"has_subjects": False, "subjects_count": 0}

class AttendanceBotAPI:
    """Класс для работы с API attendance bot"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def get_status(self) -> Dict:
        """Получить статус бота"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/status") as response:
                    if response.status == 200:
                        return await response.json()
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def start_bot(self, username: str, password: str) -> Dict:
        """Запустить attendance bot"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {"username": username, "password": password}
                async with session.get(f"{self.base_url}/attend", params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def stop_bot(self) -> Dict:
        """Остановить attendance bot"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/stop") as response:
                    if response.status == 200:
                        return await response.json()
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def check_schedule(self) -> Dict:
        """Проверить расписание"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {"url": "https://wsp.kbtu.kz/StudentSchedule"}
                async with session.get(f"{self.base_url}/check-page", params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

# Инициализация API
api = AttendanceBotAPI(ATTENDANCE_API_URL)

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Создать главную клавиатуру"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("🚀 Запустить", callback_data="start_bot")
        ],
        [
            InlineKeyboardButton("⏹️ Остановить", callback_data="stop_bot"),
            InlineKeyboardButton("📅 Расписание", callback_data="schedule")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton("ℹ️ Помощь", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    keyboard = [
        [
            InlineKeyboardButton("👤 Изменить логин", callback_data="change_username"),
            InlineKeyboardButton("🔑 Изменить пароль", callback_data="change_password")
        ],
        [
            InlineKeyboardButton("🔔 Уведомления", callback_data="toggle_notifications"),
            InlineKeyboardButton("🔄 Автозапуск", callback_data="toggle_autostart")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    global ADMIN_USER_ID
    
    user = update.effective_user
    if ADMIN_USER_ID is None:
        ADMIN_USER_ID = user.id
        logger.info(f"Admin user set to: {user.id} ({user.full_name})")
    
    if user.id not in user_data:
        user_data[user.id] = {
            "username": "",
            "password": "", 
            "notifications": True,
            "autostart": False
        }
    
    welcome_text = f"""🤖 Добро пожаловать в SeniorAtt-Bot!

Привет, {user.first_name}! 👋

Я профессиональный бот для управления вашим attendance bot КБТУ.

Возможности:
🎯 Управление attendance bot
📊 Мониторинг статуса в реальном времени
🔔 Уведомления о новых предметах
📅 Проверка расписания
⚙️ Гибкие настройки

Для начала работы:
1. Настройте логин и пароль в разделе "Настройки"
2. Запустите attendance bot
3. Получайте уведомления автоматически!

Выберите действие:"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if user_id not in user_data:
        user_data[user_id] = {
            "username": "",
            "password": "",
            "notifications": True,
            "autostart": False
        }
    
    if data == "status":
        await handle_status(query, context)
    elif data == "start_bot":
        await handle_start_bot(query, context)
    elif data == "stop_bot":
        await handle_stop_bot(query, context)
    elif data == "schedule":
        await handle_schedule(query, context)
    elif data == "settings":
        await handle_settings(query, context)
    elif data == "help":
        await handle_help(query, context)
    elif data == "back_to_main":
        await show_main_menu(query, context)
    elif data.startswith("change_"):
        await handle_change_credentials(query, context, data)
    elif data == "toggle_notifications":
        await handle_toggle_notifications(query, context)
    elif data == "toggle_autostart":
        await handle_toggle_autostart(query, context)

async def handle_status(query, context) -> None:
    """Обработка запроса статуса"""
    status_msg = await query.edit_message_text("⏳ Получаю статус бота...")
    
    try:
        status = await api.get_status()
        
        if "error" in status:
            status_text = f"""❌ Ошибка подключения

🔴 Не удается получить статус
📝 Ошибка: {status['error']}

Проверьте:
• Запущен ли Docker контейнер
• Доступность API на порту 8000"""
        else:
            running = status.get("running", False)
            message = status.get("message", "Неизвестно")
            error = status.get("last_error")
            
            status_emoji = "🟢" if running else "🔴"
            status_text_str = "Работает" if running else "Остановлен"
            
            status_text = f"""📊 Статус Attendance Bot

{status_emoji} Статус: {status_text_str}
📝 Сообщение: {message}
🕐 Время: {datetime.now().strftime('%H:%M:%S')}"""
            
            if error:
                status_text += f"\n❌ Последняя ошибка: {error}"
        
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="status")],
                   [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_msg.message_id,
            text=status_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_msg.message_id,
            text=f"❌ Ошибка при получении статуса: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )

async def handle_start_bot(query, context) -> None:
    """Запуск attendance bot"""
    user_id = query.from_user.id
    user_info = user_data[user_id]
    
    if not user_info["username"] or not user_info["password"]:
        await query.edit_message_text(
            "⚠️ Учетные данные не настроены\n\nСначала укажите логин и пароль в настройках.",
            reply_markup=get_settings_keyboard()
        )
        return
    
    status_msg = await query.edit_message_text("🚀 Запускаю attendance bot...")
    
    try:
        result = await api.start_bot(user_info["username"], user_info["password"])
        
        if "error" in result:
            # Используем простой текст без Markdown
            error_msg = str(result['error'])
            response_text = f"❌ Ошибка запуска\n\n{error_msg}"
        else:
            response_text = f"""✅ Bot запущен успешно!

👤 Пользователь: {user_info["username"]}
🚀 Статус: Запущен
🔄 Мониторинг: Активен

Bot начал работу и будет автоматически отмечать посещаемость."""
        
        keyboard = [[InlineKeyboardButton("📊 Проверить статус", callback_data="status")],
                   [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_msg.message_id,
            text=response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_msg.message_id,
            text=f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )

async def handle_stop_bot(query, context) -> None:
    """Остановка attendance bot"""
    status_msg = await query.edit_message_text("⏹️ Останавливаю attendance bot...")
    
    try:
        result = await api.stop_bot()
        
        if "error" in result:
            # Используем простой текст без Markdown
            error_msg = str(result['error'])
            response_text = f"❌ Ошибка остановки\n\n{error_msg}"
        else:
            response_text = """⏹️ Bot остановлен

🔴 Статус: Остановлен
📝 Сообщение: Bot остановлен по запросу пользователя

Для повторного запуска используйте кнопку "Запустить".
"""
        
        keyboard = [[InlineKeyboardButton("🚀 Запустить снова", callback_data="start_bot")],
                   [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_msg.message_id,
            text=response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_msg.message_id,
            text=f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )

async def handle_schedule(query, context) -> None:
    """Проверка расписания"""
    status_msg = await query.edit_message_text("📅 Загружаю расписание...")
    
    try:
        result = await api.check_schedule()
        
        if result.get("status") == "success" and "data" in result:
            data = result["data"]
            
            schedule_text = f"""
📅 Информация о расписании

📄 Заголовок: {data.get('title', 'Не определен')}
🔗 URL: {data.get('current_url', 'Неизвестно')}
📊 Размер страницы: {data.get('page_length', 0)} символов
📝 Видимый текст: {data.get('visible_text_length', 0)} символов

🔍 Найденные ключевые слова:
{', '.join(data.get('found_schedule_keywords', [])) or 'Не найдено'}

📋 Структура страницы:
• Таблицы: {'Да' if data.get('has_tables') else 'Нет'}
• Кнопки отметки: {'Да' if data.get('has_buttons') else 'Нет'}
"""
            
            if data.get('error'):
                schedule_text += f"\n⚠️ Предупреждение: {data['error']}"
            
            # Показываем превью если есть
            if data.get('visible_text_preview'):
                preview = data['visible_text_preview'][:200]
                schedule_text += f"\n\n📋 Превью:\n{preview}..."
        
        else:
            schedule_text = f"""
❌ Ошибка загрузки расписания

Не удалось получить информацию о расписании.
Ошибка: {result.get('error', 'Неизвестная ошибка')}
"""
        
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="schedule")],
                   [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_msg.message_id,
            text=schedule_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_msg.message_id,
            text=f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        )

async def handle_settings(query, context) -> None:
    """Настройки бота"""
    user_id = query.from_user.id
    user_info = user_data[user_id]
    
    settings_text = f"""
⚙️ Настройки SeniorAtt-Bot

👤 Логин: {'✅ Настроен' if user_info['username'] else '❌ Не настроен'}
🔑 Пароль: {'✅ Настроен' if user_info['password'] else '❌ Не настроен'}
🔔 Уведомления: {'✅ Включены' if user_info['notifications'] else '❌ Отключены'}
🔄 Автозапуск: {'✅ Включен' if user_info['autostart'] else '❌ Отключен'}

Выберите параметр для изменения:
"""
    
    await query.edit_message_text(
        settings_text,
        reply_markup=get_settings_keyboard()
    )

async def handle_help(query, context) -> None:
    """Справка по боту"""
    help_text = """
ℹ️ Справка по SeniorAtt-Bot

Основные функции:
🎯 Статус - Проверить состояние attendance bot
🚀 Запустить - Активировать мониторинг посещаемости
⏹️ Остановить - Деактивировать бота
📅 Расписание - Просмотр информации о расписании

Настройки:
👤 Логин/Пароль - Учетные данные КБТУ
🔔 Уведомления - Автоматические уведомления
🔄 Автозапуск - Запуск бота при старте

Уведомления:
• Появление новых предметов для отметки
• Успешная отметка посещаемости
• Ошибки в работе системы

Команды:
/start - Главное меню
/status - Быстрый статус
/help - Эта справка

Поддержка: @your_support_username
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]]
    
    await query.edit_message_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_main_menu(query, context) -> None:
    """Показать главное меню"""
    user = query.from_user
    
    main_text = f"""
🤖 SeniorAtt-Bot - Панель управления

Добро пожаловать, {user.first_name}! 

Выберите действие:
"""
    
    await query.edit_message_text(
        main_text,
        reply_markup=get_main_keyboard()
    )

async def handle_change_credentials(query, context, action) -> None:
    """Обработка изменения учетных данных"""
    if action == "change_username":
        text = """
👤 Изменение логина

Для изменения логина отправьте сообщение в формате:
/setlogin your_login@kbtu.kz

Пример: /setlogin a_daribayev@kbtu.kz
"""
    elif action == "change_password":
        text = """
🔑 Изменение пароля

Для изменения пароля отправьте сообщение в формате:
/setpassword your_password

⚠️ Внимание: Пароль будет удален из чата после обработки для безопасности.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_toggle_notifications(query, context) -> None:
    """Переключение уведомлений"""
    user_id = query.from_user.id
    user_data[user_id]["notifications"] = not user_data[user_id]["notifications"]
    
    status = "включены" if user_data[user_id]["notifications"] else "отключены"
    
    await query.answer(f"🔔 Уведомления {status}")
    await handle_settings(query, context)

async def handle_toggle_autostart(query, context) -> None:
    """Переключение автозапуска"""
    user_id = query.from_user.id
    user_data[user_id]["autostart"] = not user_data[user_id]["autostart"]
    
    status = "включен" if user_data[user_id]["autostart"] else "отключен"
    
    await query.answer(f"🔄 Автозапуск {status}")
    await handle_settings(query, context)

# Обработчики команд для настройки учетных данных
async def set_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Установка логина"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("❌ Укажите логин: /setlogin your_email@kbtu.kz")
        return
    
    login = context.args[0]
    user_data[user_id]["username"] = login
    
    await update.message.reply_text(
        f"✅ Логин установлен: {login}",
        reply_markup=get_main_keyboard()
    )
    
    # Удаляем сообщение пользователя для безопасности
    try:
        await update.message.delete()
    except:
        pass

async def set_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Установка пароля"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("❌ Укажите пароль: /setpassword your_password")
        return
    
    password = " ".join(context.args)
    user_data[user_id]["password"] = password
    
    if update.message:
        await update.message.reply_text(
            "✅ Пароль установлен успешно",
            reply_markup=get_main_keyboard()
        )
    
    # Удаляем сообщения для безопасности
    try:
        await update.message.delete()
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id - 1
        )
    except:
        pass

async def quick_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Быстрая проверка статуса"""
    try:
        status = await api.get_status()
        
        if "error" in status:
            status_text = f"❌ Ошибка: {status['error']}"
        else:
            running = status.get("running", False)
            emoji = "🟢" if running else "🔴"
            status_str = "Работает" if running else "Остановлен"
            status_text = f"{emoji} Статус: {status_str}"
        
        await update.message.reply_text(
            status_text,
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Функция мониторинга для уведомлений
async def monitor_attendance(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Мониторинг изменений в attendance bot"""
    global last_attendance_status
    
    try:
        status = await api.get_status()
        
        if "error" not in status and status.get("running"):
            # Здесь можно добавить логику проверки появления новых предметов
            # Пока что отправляем периодические обновления статуса
            
            for user_id, user_info in user_data.items():
                if user_info.get("notifications", True):
                    # Отправляем уведомление о работе бота (раз в час)
                    current_hour = datetime.now().hour
                    if current_hour % 1 == 0:  # Каждый час
                        try:
                            await context.bot.send_message(
                                chat_id=user_id,
                                text="🔄 Attendance bot работает\n\nМониторинг посещаемости активен.",
                                
                            )
                        except Exception as e:
                            logger.error(f"Failed to send notification to {user_id}: {e}")
    
    except Exception as e:
        logger.error(f"Monitor error: {e}")

def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setlogin", set_login))
    application.add_handler(CommandHandler("setpassword", set_password))
    application.add_handler(CommandHandler("status", quick_status))
    application.add_handler(CommandHandler("help", handle_help))
    
    # Добавляем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Настраиваем команды бота
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("status", "📊 Быстрый статус"), 
        BotCommand("help", "ℹ️ Справка"),
        BotCommand("setlogin", "👤 Установить логин"),
        BotCommand("setpassword", "🔑 Установить пароль")
    ]
    
    # Добавляем периодический мониторинг (если JobQueue доступен)
    try:
        job_queue = application.job_queue
        if job_queue is not None:
            job_queue.run_repeating(monitor_attendance, interval=300, first=10)  # Каждые 5 минут
            logger.info("Job queue monitoring enabled")
        else:
            logger.warning("Job queue not available, monitoring disabled")
    except Exception as e:
        logger.warning(f"Could not set up job queue: {e}")
    
    async def post_init(app):
        await app.bot.set_my_commands(commands)
        logger.info("SeniorAtt-Bot started successfully!")
    
    application.post_init = post_init
    
    # Запускаем бота
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()