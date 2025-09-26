#!/bin/bash

echo "🚀 Запуск SeniorAtt-Bot System..."
echo "=================================="

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Пожалуйста, установите Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Пожалуйста, установите Docker Compose."
    exit 1
fi

# Проверяем что Docker запущен
if ! docker info &> /dev/null; then
    echo "❌ Docker не запущен. Пожалуйста, запустите Docker."
    exit 1
fi

echo "✅ Docker проверен успешно"

# Останавливаем существующие контейнеры
echo "🛑 Останавливаем существующие контейнеры..."
docker-compose down

# Собираем и запускаем сервисы
echo "🔨 Собираем Docker образы..."
docker-compose build

echo "🚀 Запускаем сервисы..."
docker-compose up -d

# Проверяем статус
echo "📊 Проверяем статус сервисов..."
sleep 5
docker-compose ps

echo ""
echo "🎉 Система запущена успешно!"
echo ""
echo "📋 Доступные сервисы:"
echo "   🤖 Attendance Bot API: http://localhost:8000"
echo "   📱 Telegram Bot: Работает и готов к использованию"
echo ""
echo "📱 Ваш Telegram бот: @alzhandBot"
echo "🔗 Ссылка: https://t.me/alzhandBot"
echo ""
echo "🛠️ Управление:"
echo "   docker-compose logs              # Показать логи всех сервисов"
echo "   docker-compose logs telegram-bot # Логи Telegram бота" 
echo "   docker-compose logs wsp-autoattend # Логи Attendance бота"
echo "   docker-compose down             # Остановить все сервисы"
echo ""
echo "✨ Готово! Переходите в Telegram и начинайте использовать бота!"