TG-Catalog — КРАТКАЯ ИНСТРУКЦИЯ

Папка проекта:
C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog

==================================================
1. ПЕРВЫЙ ЗАПУСК
==================================================

cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
pip install -r requirements.txt
python database.py

==================================================
2. ЗАПУСК САЙТА ЛОКАЛЬНО
==================================================

cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
python -m web.app

Открыть в браузере:
http://127.0.0.1:5000

==================================================
3. ПАРСИНГ КАНАЛОВ ИЗ ВНЕШНИХ КАТАЛОГОВ
==================================================

cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
python parser\parse_catalogs.py

Результат:
parser\tg_channels.xlsx

==================================================
4. ИМПОРТ КАНАЛОВ ИЗ EXCEL В БАЗУ
==================================================

cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
python parser\import_from_excel.py

После этого можно открыть сайт:
python -m web.app

==================================================
5. ПОИСК КАНАЛОВ ЧЕРЕЗ TELEGRAM API
==================================================

Нужен заполненный .env

Запуск:
cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
python parser\crawler.py

Потом открыть сайт:
python -m web.app

==================================================
6. ЗАПУСК TELEGRAM-БОТА
==================================================

Нужен BOT_TOKEN в .env

Запуск:
cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
python bot\bot.py

==================================================
7. ВЫКАТИТЬ ИЗМЕНЕНИЯ В ИНТЕРНЕТ
==================================================

cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
git add .
git commit -m "update project"
git push origin main

После push Railway сам обновит сайт.

Публичный сайт:
https://tg-catalog-production.up.railway.app

==================================================
8. ЧТО ЗА ЧТО ОТВЕЧАЕТ
==================================================

requirements.txt
- установка библиотек

.env
- локальные секреты и настройки
- TG_API_ID
- TG_API_HASH
- PHONE
- BOT_TOKEN

.env.example
- шаблон .env без секретов

database.py
- создание и инициализация базы SQLite

web/app.py
- запуск сайта Flask
- запускать ТОЛЬКО так:
  python -m web.app

web/templates/index.html
- главная страница

web/templates/catalog.html
- каталог каналов

web/templates/channel.html
- карточка канала

web/static/style.css
- стили сайта

parser/parse_catalogs.py
- собирает каналы из внешних каталогов
- сохраняет в Excel

parser/import_from_excel.py
- грузит Excel в базу

parser/crawler.py
- собирает каналы через Telegram API

bot/bot.py
- Telegram-бот

Procfile
- нужен Railway для запуска сайта в облаке

runtime.txt
- версия Python для Railway

README.md
- основная документация проекта

==================================================
9. САМЫЕ ЧАСТЫЕ КОМАНДЫ
==================================================

Открыть сайт:
python -m web.app

Создать/проверить базу:
python database.py

Собрать Excel:
python parser\parse_catalogs.py

Импортировать Excel:
python parser\import_from_excel.py

Запустить Telegram-краулер:
python parser\crawler.py

Запустить бота:
python bot\bot.py

Отправить изменения в GitHub:
git add .
git commit -m "update"
git push origin main

==================================================
10. ВАЖНО
==================================================

НЕ запускать сайт так:
python web/app.py

ПРАВИЛЬНО:
python -m web.app

.env в GitHub не загружать.
Для Railway секреты задаются через Variables.

==================================================
11. БЫСТРЫЙ СЦЕНАРИЙ НА КАЖДЫЙ ДЕНЬ
==================================================

Если просто открыть сайт:
cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
python -m web.app

Если обновить каналы:
cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
python parser\parse_catalogs.py
python parser\import_from_excel.py
python -m web.app

Если выкатить в интернет:
cd C:\Users\Rogov\Desktop\Python\tg-catalog\tg-catalog
git add .
git commit -m "update catalog"
git push origin main