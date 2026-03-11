"""
Telegram-бот каталога каналов организаций
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode

from database import search_channels, get_stats, get_top_channels, get_db, CATEGORIES, init_db

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

ICONS = {
    "IT и технологии": "💻", "Бизнес и финансы": "🏢", "Медиа и СМИ": "📰",
    "Госорганы": "🏛", "Образование": "🎓", "Медицина": "🏥",
    "Ритейл и e-commerce": "🛒", "Промышленность": "🏭",
    "Юридические услуги": "⚖️", "Другое": "🎨",
}


def fmt(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)


@dp.message(Command("start"))
async def cmd_start(msg: Message):
    await msg.answer(
        "📡 <b>TG-Catalog Bot</b>\n\n"
        "🔍 /search &lt;запрос&gt; — поиск\n"
        "➕ /add &lt;@username&gt; — предложить канал\n"
        "📊 /stats — статистика\n"
        "🏆 /top — топ-10\n"
        "📂 /categories — категории"
    )


@dp.message(Command("search"))
async def cmd_search(msg: Message):
    q = msg.text.replace("/search", "").strip()
    if not q:
        await msg.answer("🔍 Укажи запрос: <code>/search банк</code>")
        return
    results = search_channels(q, limit=10)
    if not results:
        await msg.answer(f"😔 По «{q}» ничего не найдено")
        return
    text = f"🔍 «{q}»:\n\n"
    for i, ch in enumerate(results, 1):
        text += f"{i}. <b>{ch['title']}</b>\n   @{ch['username']} · {fmt(ch['subscribers'])} подп.\n   {ICONS.get(ch['category'], '📁')} {ch['category']}\n\n"
    await msg.answer(text)


@dp.message(Command("add"))
async def cmd_add(msg: Message):
    username = msg.text.replace("/add", "").strip().lstrip("@")
    if not username:
        await msg.answer("➕ Укажи: <code>/add @channel</code>")
        return
    conn = get_db()
    if conn.execute("SELECT id FROM channels WHERE username=?", (username,)).fetchone():
        await msg.answer(f"✅ @{username} уже в каталоге!")
        conn.close()
        return
    try:
        conn.execute("INSERT INTO user_submissions (username, submitted_by) VALUES (?, ?)", (username, msg.from_user.id))
        conn.commit()
        await msg.answer(f"📝 @{username} отправлен на модерацию!")
    except:
        await msg.answer(f"⚠️ @{username} уже в очереди")
    finally:
        conn.close()


@dp.message(Command("stats"))
async def cmd_stats(msg: Message):
    s = get_stats()
    text = f"📊 <b>Статистика</b>\n\n🏢 Организаций: <b>{s['total_orgs']}</b>\n📡 Всего: <b>{s['total_all']}</b>\n\n"
    for c in s["categories"]:
        text += f"  {ICONS.get(c['category'], '📁')} {c['category']}: {c['cnt']}\n"
    await msg.answer(text)


@dp.message(Command("top"))
async def cmd_top(msg: Message):
    channels = get_top_channels(10)
    if not channels:
        await msg.answer("📭 Каталог пуст — запусти парсер!")
        return
    text = "🏆 <b>Топ-10</b>\n\n"
    for i, ch in enumerate(channels, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        text += f"{medal} <b>{ch['title']}</b>\n    @{ch['username']} · {fmt(ch['subscribers'])}\n\n"
    await msg.answer(text)


@dp.message(Command("categories"))
async def cmd_cats(msg: Message):
    s = get_stats()
    text = "📂 <b>Категории</b>\n\n"
    for c in s["categories"]:
        text += f"{ICONS.get(c['category'], '📁')} {c['category']} — {c['cnt']}\n"
    await msg.answer(text)


async def main():
    init_db()
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
