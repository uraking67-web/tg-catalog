"""
Импорт каналов из Excel в базу TG-Catalog

Запуск:
    python import_from_excel.py tg_channels.xlsx

Читает Excel-файл и добавляет каналы в SQLite базу проекта.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openpyxl import load_workbook
from database import add_channel, get_db, init_db


def import_excel(filepath):
    """Импорт каналов из Excel."""
    if not os.path.exists(filepath):
        print(f"[!] Файл не найден: {filepath}")
        return

    init_db()

    wb = load_workbook(filepath, read_only=True)
    ws = wb.active

    added = 0
    skipped = 0
    total = 0

    print(f"📥 Импорт из {filepath}...")

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or len(row) < 3:
            continue

        total += 1
        # Колонки: #, Username, Название, Подписчики, Категория, Описание, Источник
        username = str(row[1] or "").strip().lstrip("@")
        title = str(row[2] or "").strip()
        subscribers = int(row[3] or 0) if row[3] else 0
        category = str(row[4] or "Другое").strip() if len(row) > 4 else "Другое"
        description = str(row[5] or "").strip() if len(row) > 5 else ""

        if not username or not title:
            skipped += 1
            continue

        # Проверяем нет ли уже в базе
        conn = get_db()
        existing = conn.execute("SELECT id FROM channels WHERE username=?", (username,)).fetchone()
        conn.close()

        if existing:
            skipped += 1
            continue

        # Генерируем фейковый tg_id (будет обновлён при следующем запуске краулера)
        fake_tg_id = hash(username) % 2_000_000_000

        success = add_channel(
            tg_id=fake_tg_id,
            username=username,
            title=title,
            description=description,
            subscribers=subscribers,
            is_verified=False,
            source="excel_import",
            found_via="catalog_parser"
        )

        if success:
            added += 1
            if added % 50 == 0:
                print(f"  ... {added} добавлено")
        else:
            skipped += 1

    wb.close()

    print(f"\n✅ Импорт завершён!")
    print(f"   📊 Всего строк: {total}")
    print(f"   ✅ Добавлено: {added}")
    print(f"   ⏭  Пропущено: {skipped}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # По умолчанию ищем файл рядом
        default = os.path.join(os.path.dirname(__file__), "tg_channels.xlsx")
        if os.path.exists(default):
            import_excel(default)
        else:
            print("Использование: python import_from_excel.py <path_to_excel.xlsx>")
    else:
        import_excel(sys.argv[1])
