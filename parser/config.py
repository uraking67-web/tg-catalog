"""
Конфигурация парсера. Загружает переменные из .env
"""

import os
from dotenv import load_dotenv

# Загружаем .env из корня проекта (на уровень выше parser/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Telegram API
API_ID = int(os.getenv("TG_API_ID", os.getenv("API_ID", "0")))
API_HASH = os.getenv("TG_API_HASH", os.getenv("API_HASH", ""))
PHONE = os.getenv("PHONE", "")

# Лимиты парсинга
MAX_CHANNELS = int(os.getenv("MAX_CHANNELS", "5000"))
CRAWL_DEPTH = int(os.getenv("CRAWL_DEPTH", "3"))
DELAY_BETWEEN_REQUESTS = float(os.getenv("DELAY_BETWEEN_REQUESTS", "2"))

# Сколько последних постов анализировать
POSTS_TO_SCAN = 100

# Минимум подписчиков
MIN_SUBSCRIBERS = 100

# Проверка при импорте
if API_ID == 0 or not API_HASH:
    print("[!] ОШИБКА: TG_API_ID или TG_API_HASH не найдены!")
    print(f"    Искали .env в: {os.path.join(os.path.dirname(__file__), '..', '.env')}")
    print(f"    Файл существует: {os.path.exists(os.path.join(os.path.dirname(__file__), '..', '.env'))}")
else:
    print(f"[✓] API_ID={API_ID}, HASH={API_HASH[:8]}..., PHONE={PHONE}")
