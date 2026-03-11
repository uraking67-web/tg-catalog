"""
Краулер Telegram-каналов организаций (АВТОПОИСК)

Сам ищет каналы! Не нужен seeds.txt.

Как работает:
1. Ищет каналы через глобальный поиск Telegram по ключевым словам
2. Для каждого найденного канала получает метаданные
3. Сканирует посты на пересылки → находит ещё каналы
4. Рекурсивно обходит всё найденное
5. Фильтрует по признакам организаций
6. Сохраняет в SQLite
"""

import asyncio
import os
import sys
import re
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel
from telethon.errors import (
    ChannelPrivateError, UsernameNotOccupiedError,
    FloodWaitError, ChannelInvalidError
)

from config import (
    API_ID, API_HASH, PHONE,
    MAX_CHANNELS, CRAWL_DEPTH, DELAY_BETWEEN_REQUESTS,
    POSTS_TO_SCAN, MIN_SUBSCRIBERS
)
from database import get_db, add_channel, init_db

# ─── Клиент ───
SESSION_PATH = os.path.join(os.path.dirname(__file__), "crawler_session")
client = TelegramClient(SESSION_PATH, API_ID, API_HASH)

# Статистика
stats = {"scanned": 0, "added": 0, "skipped": 0, "errors": 0, "start_time": None}

# ─── Ключевые слова для автопоиска организаций ───
SEARCH_KEYWORDS = [
    # Бизнес
    "компания официальный", "банк официальный", "бизнес россия",
    "корпорация", "холдинг", "группа компаний",
    "финансы официальный", "инвестиции фонд",
    # IT
    "IT компания", "разработка ПО", "стартап технологии",
    "digital агентство", "software company",
    "кибербезопасность", "облачные сервисы",
    # Медиа
    "новости официальный", "СМИ канал", "информагентство",
    "редакция новости", "медиа издание",
    # Госструктуры
    "министерство официальный", "правительство",
    "администрация города", "департамент",
    "госуслуги", "мэрия",
    # Образование
    "университет официальный", "институт",
    "академия", "образование курсы",
    # Медицина
    "клиника официальный", "медицинский центр",
    "больница", "фармацевтическая компания",
    # Ритейл
    "магазин официальный", "маркетплейс",
    "доставка еды", "торговая сеть",
    # Промышленность
    "завод официальный", "производство",
    "нефтегазовая компания", "энергетическая компания",
    # Юрид
    "юридическая компания", "адвокатское бюро",
    # Общие
    "official channel", "пресс-служба",
    "служба поддержки", "вакансии компания",
    "HR официальный", "ООО", "ПАО",
]


def add_to_queue(username, depth):
    conn = get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO crawl_queue (username, depth) VALUES (?, ?)", (username, depth))
        conn.commit()
    finally:
        conn.close()


def get_next_from_queue(batch_size=10):
    conn = get_db()
    rows = conn.execute("""
        SELECT id, username, depth FROM crawl_queue
        WHERE status = 'pending' ORDER BY depth ASC, id ASC LIMIT ?
    """, (batch_size,)).fetchall()
    if rows:
        ids = [r["id"] for r in rows]
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"UPDATE crawl_queue SET status='processing' WHERE id IN ({placeholders})", ids)
        conn.commit()
    conn.close()
    return [dict(r) for r in rows]


def mark_queue_done(username, status="done"):
    conn = get_db()
    conn.execute("UPDATE crawl_queue SET status=? WHERE username=?", (status, username))
    conn.commit()
    conn.close()


def log_action(username, action, details=""):
    conn = get_db()
    conn.execute("INSERT INTO crawl_log (channel_username, action, details) VALUES (?, ?, ?)",
                 (username, action, details))
    conn.commit()
    conn.close()


async def search_channels_by_keyword(keyword):
    """Поиск каналов через глобальный поиск Telegram."""
    found = []
    try:
        result = await client(SearchRequest(q=keyword, limit=100))
        for chat in result.chats:
            if isinstance(chat, Channel) and chat.username:
                found.append(chat.username)
        print(f"  🔎 «{keyword}» → найдено {len(found)} каналов")
    except FloodWaitError as e:
        print(f"  [⏳] FloodWait при поиске: ждём {e.seconds}с...")
        await asyncio.sleep(e.seconds + 1)
        return await search_channels_by_keyword(keyword)
    except Exception as e:
        print(f"  [!] Ошибка поиска «{keyword}»: {e}")
    return found


async def auto_discover_seeds():
    """Автоматический поиск каналов по ключевым словам."""
    print(f"\n🔍 АВТОПОИСК: {len(SEARCH_KEYWORDS)} ключевых запросов...\n")

    all_found = set()
    for i, keyword in enumerate(SEARCH_KEYWORDS, 1):
        print(f"[{i}/{len(SEARCH_KEYWORDS)}]", end="")
        channels = await search_channels_by_keyword(keyword)
        for ch in channels:
            all_found.add(ch)
        await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n📡 Автопоиск завершён! Найдено {len(all_found)} уникальных каналов\n")
    return list(all_found)


async def get_channel_info(username):
    try:
        entity = await client.get_entity(username)
        if not isinstance(entity, Channel):
            return None
        full = await client(GetFullChannelRequest(entity))
        return {
            "tg_id": entity.id,
            "username": entity.username or username,
            "title": entity.title,
            "description": full.full_chat.about or "",
            "subscribers": full.full_chat.participants_count or 0,
            "is_verified": getattr(entity, "verified", False),
        }
    except ChannelPrivateError:
        log_action(username, "skip", "Приватный канал")
        return None
    except UsernameNotOccupiedError:
        log_action(username, "skip", "Username не существует")
        return None
    except ChannelInvalidError:
        log_action(username, "skip", "Невалидный канал")
        return None
    except FloodWaitError as e:
        print(f"  [⏳] FloodWait: ждём {e.seconds}с...")
        await asyncio.sleep(e.seconds + 1)
        return await get_channel_info(username)
    except Exception as e:
        log_action(username, "error", str(e))
        return None


async def find_forwards(username, limit=POSTS_TO_SCAN):
    found = set()
    try:
        entity = await client.get_entity(username)
        async for msg in client.iter_messages(entity, limit=limit):
            # Пересылки
            if msg.forward and msg.forward.chat:
                fwd = msg.forward.chat
                if isinstance(fwd, Channel) and fwd.username:
                    found.add(fwd.username)
            # Ссылки в тексте
            if msg.text:
                links = re.findall(r"(?:t\.me/|@)([a-zA-Z_][a-zA-Z0-9_]{3,30})", msg.text)
                for link in links:
                    if link.lower() not in ("username", "bot", "botfather", "telegram"):
                        found.add(link)
            # Кнопки
            if msg.reply_markup:
                try:
                    for row in msg.reply_markup.rows:
                        for btn in row.buttons:
                            if hasattr(btn, "url") and btn.url:
                                m = re.search(r"t\.me/([a-zA-Z_][a-zA-Z0-9_]{3,30})", btn.url)
                                if m:
                                    found.add(m.group(1))
                except Exception:
                    pass
    except Exception as e:
        log_action(username, "forward_scan_error", str(e))
    found.discard(username)
    return list(found)


async def process_channel(username, depth):
    stats["scanned"] += 1
    print(f"\n[{stats['scanned']}] 🔍 @{username} (глубина {depth})...")

    info = await get_channel_info(username)
    if not info:
        stats["skipped"] += 1
        mark_queue_done(username, "error")
        return

    if info["subscribers"] < MIN_SUBSCRIBERS:
        stats["skipped"] += 1
        mark_queue_done(username, "done")
        print(f"  ⏭ Пропуск ({info['subscribers']} подп.)")
        return

    added = add_channel(
        tg_id=info["tg_id"], username=info["username"],
        title=info["title"], description=info["description"],
        subscribers=info["subscribers"], is_verified=info["is_verified"],
        source="crawler", found_via=f"depth_{depth}"
    )

    if added:
        stats["added"] += 1
        print(f"  ✅ {info['title']} | {info['subscribers']:,} подп.")
    else:
        stats["errors"] += 1

    # Рекурсивный поиск через пересылки
    if depth < CRAWL_DEPTH:
        await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
        forwards = await find_forwards(username)
        for fwd in forwards:
            add_to_queue(fwd, depth + 1)
        if forwards:
            print(f"  📡 +{len(forwards)} связанных каналов в очередь")

    mark_queue_done(username, "done")
    await asyncio.sleep(DELAY_BETWEEN_REQUESTS)


async def run_crawler():
    print("=" * 60)
    print("🕷  TG-Catalog Crawler (АВТОПОИСК)")
    print("=" * 60)
    stats["start_time"] = time.time()
    init_db()

    print(f"⚙️  Макс: {MAX_CHANNELS} | Глубина: {CRAWL_DEPTH} | Задержка: {DELAY_BETWEEN_REQUESTS}с")

    # ШАГ 1: Автоматический поиск через Telegram
    seeds = await auto_discover_seeds()

    if not seeds:
        print("[!] Ничего не найдено через поиск. Проверь подключение.")
        return

    # Добавляем всё в очередь
    for seed in seeds:
        add_to_queue(seed, depth=0)

    print(f"📋 В очереди: {len(seeds)} каналов. Начинаем обход...\n")

    # ШАГ 2: Обход каналов + рекурсивный поиск через пересылки
    while stats["added"] < MAX_CHANNELS:
        batch = get_next_from_queue(batch_size=5)
        if not batch:
            print("\n✅ Очередь пуста — обход завершён!")
            break
        for item in batch:
            if stats["added"] >= MAX_CHANNELS:
                break
            await process_channel(item["username"], item["depth"])

    elapsed = time.time() - stats["start_time"]
    print(f"\n{'=' * 60}")
    print(f"📊 ИТОГИ: {elapsed:.0f}с")
    print(f"   🔍 Просканировано: {stats['scanned']}")
    print(f"   ✅ Добавлено: {stats['added']}")
    print(f"   ⏭  Пропущено: {stats['skipped']}")
    print(f"   ❌ Ошибок: {stats['errors']}")
    print("=" * 60)


async def main():
    await client.start(phone=PHONE)
    me = await client.get_me()
    print(f"✅ Авторизован: {me.first_name}")
    await run_crawler()
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
