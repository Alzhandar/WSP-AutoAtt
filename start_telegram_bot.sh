#!/bin/bash
echo "🤖 Запуск SeniorAtt-Bot (Telegram Bot)..."

# Проверяем наличие Python зависимостей
echo "📦 Устанавливаем зависимости..."
pip3 install -r telegram_requirements.txt

# Запускаем Telegram бота
echo "🚀 Запускаем Telegram бот..."
python3 telegram_bot.py