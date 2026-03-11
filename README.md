# TG-Catalog — Каталог Telegram-каналов организаций

## Быстрый старт

### 1. Установи зависимости
```
pip install -r requirements.txt
```

### 2. Заполни seeds.txt
Открой `parser/seeds.txt` и впиши реальные username каналов (без @), по одному на строку.

### 3. Запусти парсер
```
cd parser
python crawler.py
```
При первом запуске введи код из Telegram.

### 4. Запусти сайт
```
cd web
python app.py
```
Открой http://localhost:5000

### 5. Запусти бота
```
cd bot
python bot.py
```

## Структура
```
tg-catalog/
├── .env              ← Твои креды (уже заполнен!)
├── database.py       ← Общая БД
├── parser/
│   ├── config.py     ← Конфиг
│   ├── crawler.py    ← Парсер
│   └── seeds.txt     ← Стартовые каналы
├── web/
│   ├── app.py        ← Flask-сайт
│   ├── static/       ← CSS
│   └── templates/    ← HTML
├── bot/
│   └── bot.py        ← Telegram-бот
└── data/
    └── catalog.db    ← SQLite (создаётся сам)
```
