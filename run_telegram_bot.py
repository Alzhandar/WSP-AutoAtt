#!/usr/bin/env python3
"""
🤖 SeniorAtt-Bot - Telegram Bot для управления attendance bot

Запуск: python3 telegram_bot.py
Требования: pip3 install -r telegram_requirements.txt
"""

import asyncio
import logging
import sys
from telegram_bot import main

if __name__ == '__main__':
    print("🤖 Запуск SeniorAtt-Bot...")
    print("📋 Проверьте что Docker контейнер запущен на порту 8000")
    print("🚀 Запускаем Telegram бота...")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 SeniorAtt-Bot остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)