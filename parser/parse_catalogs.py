"""
Парсер каталогов Telegram-каналов → Excel

Собирает каналы с открытых каталогов:
- tlgrm.ru (все категории)
- telegram.org.ru

Сохраняет в Excel: username, название, подписчики, категория, описание
"""

import requests
import re
import time
import os
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

all_channels = {}  # username -> {title, subscribers, category, description, source}


# ─── Парсер tlgrm.ru ───

TLGRM_CATEGORIES = {
    "news": "Медиа и СМИ",
    "tech": "IT и технологии",
    "economics": "Бизнес и финансы",
    "business": "Бизнес и финансы",
    "education": "Образование",
    "medicine": "Медицина",
    "marketing": "Бизнес и финансы",
    "law": "Юридические услуги",
    "politics": "Госорганы",
    "design": "IT и технологии",
    "crypto": "Бизнес и финансы",
    "travel": "Другое",
    "sport": "Другое",
    "science": "Образование",
    "music": "Другое",
    "food": "Другое",
    "psychology": "Другое",
    "fashion": "Другое",
    "humor": "Другое",
    "blogs": "Другое",
    "apps": "IT и технологии",
    "career": "Бизнес и финансы",
    "edutainment": "Образование",
    "courses": "Образование",
    "sales": "Ритейл и e-commerce",
    "transport": "Промышленность",
    "health": "Медицина",
    "nature": "Другое",
    "family": "Другое",
    "interior": "Другое",
    "video": "Другое",
    "games": "Другое",
    "books": "Образование",
    "linguistics": "Образование",
    "art": "Другое",
    "pictures": "Другое",
    "quotes": "Другое",
    "handmade": "Другое",
    "religion": "Другое",
    "telegram": "IT и технологии",
    "instagram": "Другое",
    "other": "Другое",
}


def parse_tlgrm_category(category_slug):
    """Парсить одну категорию с tlgrm.ru."""
    url = f"https://tlgrm.ru/channels/{category_slug}"
    category_name = TLGRM_CATEGORIES.get(category_slug, "Другое")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"    [!] HTTP {resp.status_code}")
            return 0

        soup = BeautifulSoup(resp.text, "html.parser")

        count = 0
        # Ищем ссылки вида /channels/@username
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            m = re.search(r"/channels/@([a-zA-Z_][a-zA-Z0-9_]+)", href)
            if not m:
                continue

            username = m.group(1)
            if username in all_channels:
                continue

            # Ищем название и описание рядом
            parent = link.find_parent("div") or link.find_parent("li") or link.parent
            title_el = link.find("h3") or link.find("strong") or link
            title = title_el.get_text(strip=True) if title_el else username

            # Подписчики — ищем число рядом
            subs = 0
            text_around = parent.get_text() if parent else ""
            nums = re.findall(r"([\d,]+(?:\.\d+)?)\s*$", title_el.get_text() if title_el else "")
            # Ищем число подписчиков в тексте карточки
            subs_match = re.findall(r"([\d,]{4,})", text_around.replace(" ", ""))
            for s in subs_match:
                try:
                    n = int(s.replace(",", ""))
                    if n > subs and n < 100_000_000:
                        subs = n
                except:
                    pass

            # Описание
            desc = ""
            for p in (parent.find_all("p") if parent else []):
                t = p.get_text(strip=True)
                if t and len(t) > 10 and username not in t:
                    desc = t[:300]
                    break

            all_channels[username] = {
                "title": title,
                "subscribers": subs,
                "category": category_name,
                "description": desc,
                "source": "tlgrm.ru",
            }
            count += 1

        return count

    except Exception as e:
        print(f"    [!] Ошибка: {e}")
        return 0


def parse_tlgrm():
    """Парсить все категории с tlgrm.ru."""
    print("\n" + "=" * 60)
    print("📡 Парсим tlgrm.ru")
    print("=" * 60)

    total = 0
    for slug in TLGRM_CATEGORIES:
        print(f"  [{slug}]", end=" ")
        count = parse_tlgrm_category(slug)
        total += count
        print(f"→ +{count} (всего: {len(all_channels)})")
        time.sleep(1)

    print(f"\n✅ tlgrm.ru: добавлено {total} каналов")


# ─── Парсер telegram.org.ru ───

def parse_telegram_org_ru():
    """Парсить telegram.org.ru."""
    print("\n" + "=" * 60)
    print("📡 Парсим telegram.org.ru")
    print("=" * 60)

    url = "https://telegram.org.ru/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  [!] HTTP {resp.status_code}")
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        count = 0

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            # Ищем ссылки на t.me/username
            m = re.search(r"t\.me/([a-zA-Z_][a-zA-Z0-9_]{3,30})", href)
            if not m:
                continue

            username = m.group(1)
            if username in all_channels or username.lower() in ("joinchat", "addstickers", "share"):
                continue

            title = link.get_text(strip=True) or username

            # Описание
            desc = ""
            parent = link.find_parent("div")
            if parent:
                for p in parent.find_all(["p", "span", "div"]):
                    t = p.get_text(strip=True)
                    if t and len(t) > 20 and username not in t and title not in t:
                        desc = t[:300]
                        break

            all_channels[username] = {
                "title": title if len(title) > 1 else username,
                "subscribers": 0,
                "category": "Другое",
                "description": desc,
                "source": "telegram.org.ru",
            }
            count += 1

        print(f"✅ telegram.org.ru: +{count} каналов")

    except Exception as e:
        print(f"  [!] Ошибка: {e}")


# ─── Сохранение в Excel ───

def save_to_excel(filepath="tg_channels.xlsx"):
    """Сохранить все каналы в Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Каналы"

    # Стили
    header_font = Font(name="Arial", bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1B5E20")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    # Заголовки
    headers = ["#", "Username", "Название", "Подписчики", "Категория", "Описание", "Источник"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # Сортируем по подписчикам
    sorted_channels = sorted(all_channels.items(), key=lambda x: x[1]["subscribers"], reverse=True)

    for i, (username, data) in enumerate(sorted_channels, 1):
        row = i + 1
        ws.cell(row=row, column=1, value=i).border = thin_border
        ws.cell(row=row, column=2, value=f"@{username}").border = thin_border
        ws.cell(row=row, column=3, value=data["title"]).border = thin_border
        ws.cell(row=row, column=4, value=data["subscribers"]).border = thin_border
        ws.cell(row=row, column=5, value=data["category"]).border = thin_border
        ws.cell(row=row, column=6, value=data["description"]).border = thin_border
        ws.cell(row=row, column=7, value=data["source"]).border = thin_border

        # Чередование цветов строк
        if i % 2 == 0:
            fill = PatternFill("solid", fgColor="E8F5E9")
            for col in range(1, 8):
                ws.cell(row=row, column=col).fill = fill

    # Ширина колонок
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 35
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 25
    ws.column_dimensions["F"].width = 60
    ws.column_dimensions["G"].width = 18

    # Автофильтр
    ws.auto_filter.ref = f"A1:G{len(sorted_channels) + 1}"

    # Замораживаем заголовок
    ws.freeze_panes = "A2"

    wb.save(filepath)
    print(f"\n💾 Сохранено в {filepath}: {len(sorted_channels)} каналов")


# ─── Главная ───

def main():
    print("=" * 60)
    print("🔍 Парсер каталогов Telegram-каналов → Excel")
    print("=" * 60)

    parse_tlgrm()
    parse_telegram_org_ru()

    print(f"\n📊 ИТОГО: {len(all_channels)} уникальных каналов")

    # Сохраняем
    output_path = os.path.join(os.path.dirname(__file__), "tg_channels.xlsx")
    save_to_excel(output_path)

    # Статистика по категориям
    cats = {}
    for ch in all_channels.values():
        cat = ch["category"]
        cats[cat] = cats.get(cat, 0) + 1

    print("\n📂 По категориям:")
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {cnt}")


if __name__ == "__main__":
    main()
