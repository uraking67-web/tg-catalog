import asyncio
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env", override=True)
print("BASE_DIR =", BASE_DIR)
print("ENV_FILE =", BASE_DIR / ".env")
print("BOT_TOKEN_PREFIX =", os.getenv("BOT_TOKEN", "")[:20])

from database import search_channels, get_stats, get_top_channels, init_db  # noqa: E402

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise ValueError("В .env не найден BOT_TOKEN")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


def format_channel(channel: dict) -> str:
    title = channel.get("title") or channel.get("username") or "Без названия"
    username = channel.get("username") or ""
    category = channel.get("category") or "Без категории"
    subscribers = channel.get("subscribers") or 0
    description = (channel.get("description") or "").strip()

    text = [
        f"<b>{title}</b>",
        f"@{username}",
        f"Категория: {category}",
        f"Подписчики: {subscribers}",
    ]

    if description:
        short_desc = description[:300]
        if len(description) > 300:
            short_desc += "..."
        text.append("")
        text.append(short_desc)

    return "\n".join(text)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "<b>TG-Catalog Bot</b>\n\n"
        "Команды:\n"
        "/start — старт\n"
        "/help — помощь\n"
        "/stats — статистика\n"
        "/top — топ каналов\n"
        "/find <запрос> — поиск каналов\n\n"
        "Пример:\n"
        "<code>/find ozon</code>"
    )
    await message.answer(text)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "<b>Доступные команды</b>\n\n"
        "/stats — общая статистика\n"
        "/top — топ каналов по подписчикам\n"
        "/find <запрос> — поиск по названию, username и описанию\n\n"
        "Пример:\n"
        "<code>/find банк</code>"
    )
    await message.answer(text)


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = get_stats()
    text = (
        "<b>Статистика каталога</b>\n\n"
        f"Всего каналов: <b>{stats['total_channels']}</b>\n"
        f"Организаций: <b>{stats['organizations']}</b>\n"
        f"Категорий: <b>{stats['categories']}</b>"
    )
    await message.answer(text)


@dp.message(Command("top"))
async def cmd_top(message: Message):
    channels = get_top_channels(limit=10)

    if not channels:
        await message.answer("Топ пока пуст.")
        return

    parts = ["<b>Топ каналов</b>\n"]
    for i, channel in enumerate(channels, start=1):
        title = channel.get("title") or channel.get("username") or "Без названия"
        username = channel.get("username") or ""
        subscribers = channel.get("subscribers") or 0
        parts.append(f"{i}. <b>{title}</b> — @{username} — {subscribers}")

    await message.answer("\n".join(parts))


@dp.message(Command("find"))
async def cmd_find(message: Message):
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Использование: <code>/find ваш_запрос</code>")
        return

    query = parts[1].strip()
    results = search_channels(query=query, limit=10)

    if not results:
        await message.answer(f"По запросу <b>{query}</b> ничего не найдено.")
        return

    messages = [f"<b>Результаты поиска:</b> {query}\n"]
    for channel in results:
        messages.append(format_channel(channel))
        messages.append("")

    await message.answer("\n".join(messages[:50]))


@dp.message(F.text)
async def fallback_search(message: Message):
    query = (message.text or "").strip()
    if not query:
        return

    results = search_channels(query=query, limit=5)

    if not results:
        await message.answer("Ничего не найдено. Попробуй команду /find запрос")
        return

    parts = [f"<b>Найдено по запросу:</b> {query}\n"]
    for channel in results:
        parts.append(format_channel(channel))
        parts.append("")

    await message.answer("\n".join(parts[:40]))


async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    print(f"🤖 Бот запущен: @{me.username} | id={me.id}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())