# TG-Catalog

Каталог Telegram-каналов организаций и компаний.

## Что умеет проект

- собирать каналы через Telegram API (`parser/crawler.py`)
- парсить внешние каталоги и сохранять результат в Excel (`parser/parse_catalogs.py`)
- импортировать Excel в базу (`parser/import_from_excel.py`)
- показывать каталог через Flask (`web/app.py`)
- запускать Telegram-бота (`bot/bot.py`)

## Структура проекта

- `web/` — сайт
- `parser/` — парсеры и импорт
- `bot/` — Telegram-бот
- `data/` — SQLite база
- `database.py` — работа с базой

## Локальный запуск

### 1. Установить зависимости

```bash
pip install -r requirements.txt