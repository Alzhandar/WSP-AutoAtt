#!/usr/bin/env python3
"""
Скрипт для исправления проблем с Markdown в telegram_bot.py
"""

def fix_telegram_bot():
    with open('/Users/lzandaribaev/Desktop/WSP-AutoAtt/telegram_bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Список замен для удаления parse_mode=ParseMode.MARKDOWN
    replacements = [
        # Удаляем parse_mode с запятой до
        (', parse_mode=ParseMode.MARKDOWN', ''),
        (',\n            parse_mode=ParseMode.MARKDOWN', ''),
        (',\n        parse_mode=ParseMode.MARKDOWN', ''),
        # Удаляем parse_mode с запятой после
        ('parse_mode=ParseMode.MARKDOWN,', ''),
        ('parse_mode=ParseMode.MARKDOWN,\n            ', ''),
        ('parse_mode=ParseMode.MARKDOWN,\n        ', ''),
        # Удаляем parse_mode без запятой
        ('parse_mode=ParseMode.MARKDOWN', ''),
        # Убираем лишние звездочки в тексте
        ('**', ''),
        # Убираем обратные кавычки из текста
        ('`', ''),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Убираем импорт ParseMode если он не используется
    if 'ParseMode.MARKDOWN' not in content and 'ParseMode.HTML' not in content:
        content = content.replace('from telegram.constants import ParseMode\n', '')
        content = content.replace(', ParseMode', '')
    
    with open('/Users/lzandaribaev/Desktop/WSP-AutoAtt/telegram_bot.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Файл telegram_bot.py исправлен!")

if __name__ == '__main__':
    fix_telegram_bot()