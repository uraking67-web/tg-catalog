"""
Общий модуль базы данных для всех компонентов.
SQLite + общие функции для парсера, сайта и бота.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "catalog.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            username TEXT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            subscribers INTEGER DEFAULT 0,
            category TEXT DEFAULT 'Другое',
            avatar_url TEXT DEFAULT '',
            is_verified INTEGER DEFAULT 0,
            is_organization INTEGER DEFAULT 0,
            source TEXT DEFAULT 'crawler',
            found_via TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS crawl_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            depth INTEGER DEFAULT 0,
            added_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS crawl_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT,
            action TEXT,
            details TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            submitted_by INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_channels_category ON channels(category);
        CREATE INDEX IF NOT EXISTS idx_channels_subscribers ON channels(subscribers DESC);
        CREATE INDEX IF NOT EXISTS idx_channels_username ON channels(username);
        CREATE INDEX IF NOT EXISTS idx_crawl_queue_status ON crawl_queue(status);
    """)
    conn.commit()
    conn.close()


# ─── Категории и ключевые слова ───

CATEGORIES = {
    "IT и технологии": [
        "разработ", "програм", "код", "софт", "tech", "dev", "IT", "digital",
        "startup", "стартап", "api", "software", "saas", "cloud", "облач",
        "искусственн", "нейросет", "machine learning", "data", "кибер", "инфобез"
    ],
    "Бизнес и финансы": [
        "бизнес", "финанс", "инвестиц", "банк", "экономик", "трейд",
        "business", "finance", "invest", "фонд", "капитал", "брокер",
        "страхов", "консалтинг", "аудит", "бухгалтер"
    ],
    "Медиа и СМИ": [
        "новости", "news", "медиа", "media", "журнал", "газет", "издани",
        "редакци", "пресс", "информагент", "телеканал", "радио"
    ],
    "Госорганы": [
        "министерств", "правительств", "администрац", "федеральн", "департамент",
        "ведомств", "госуслуг", "мэри", "губернатор", "дума", "совет федерац"
    ],
    "Образование": [
        "универс", "институт", "академи", "школ", "образован", "обучен",
        "курс", "лекци", "студент", "вуз", "колледж", "education"
    ],
    "Медицина": [
        "медицин", "здоровь", "клиник", "больниц", "врач", "доктор",
        "фарма", "лечени", "диагност", "health", "medical"
    ],
    "Ритейл и e-commerce": [
        "магазин", "shop", "store", "маркетплейс", "доставк", "торговл",
        "ритейл", "retail", "ecommerce", "wildberries", "ozon", "товар"
    ],
    "Промышленность": [
        "завод", "производств", "промышлен", "фабрик", "manufacturing",
        "industrial", "добыч", "нефт", "газпром", "энерг", "металл"
    ],
    "Юридические услуги": [
        "юрид", "адвокат", "право", "закон", "legal", "law", "нотариус",
        "судеб", "арбитраж"
    ],
}


def detect_category(title, description):
    text = f"{title} {description}".lower()
    scores = {}
    for category, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scores[category] = score
    if scores:
        return max(scores, key=scores.get)
    return "Другое"


def is_likely_organization(title, description, is_verified=False):
    if is_verified:
        return True
    org_signals = [
        "официальн", "official", "компани", "company", "корпорац",
        "ооо", "оао", "ао ", "зао", "пао", "inc", "ltd", "llc", "gmbh",
        "группа компаний", "холдинг", "®", "™",
        "служба поддержки", "пресс-служб", "hr ", "вакансии"
    ]
    text = f"{title} {description}".lower()
    return any(signal in text for signal in org_signals)


# ─── CRUD ───

def add_channel(tg_id, username, title, description="", subscribers=0,
                is_verified=False, source="crawler", found_via=""):
    category = detect_category(title, description)
    is_org = is_likely_organization(title, description, is_verified)
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO channels (tg_id, username, title, description, subscribers,
                                  category, is_verified, is_organization, source, found_via)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                subscribers=excluded.subscribers,
                category=excluded.category,
                is_verified=excluded.is_verified,
                updated_at=datetime('now')
        """, (tg_id, username, title, description, subscribers,
              category, int(is_verified), int(is_org), source, found_via))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return False
    finally:
        conn.close()


def search_channels(query, limit=20, offset=0):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM channels
        WHERE (title LIKE ? OR description LIKE ? OR username LIKE ?)
          AND is_organization = 1
        ORDER BY subscribers DESC
        LIMIT ? OFFSET ?
    """, (f"%{query}%", f"%{query}%", f"%{query}%", limit, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_channels_by_category(category, limit=50, offset=0):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM channels
        WHERE category = ? AND is_organization = 1
        ORDER BY subscribers DESC
        LIMIT ? OFFSET ?
    """, (category, limit, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_channels(limit=50, offset=0, sort="subscribers"):
    sort_col = "subscribers DESC" if sort == "subscribers" else "created_at DESC"
    conn = get_db()
    rows = conn.execute(f"""
        SELECT * FROM channels
        WHERE is_organization = 1
        ORDER BY {sort_col}
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM channels WHERE is_organization=1").fetchone()[0]
    total_all = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
    categories = conn.execute("""
        SELECT category, COUNT(*) as cnt FROM channels
        WHERE is_organization=1
        GROUP BY category ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    return {"total_orgs": total, "total_all": total_all, "categories": [dict(c) for c in categories]}


def get_top_channels(limit=10):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM channels WHERE is_organization = 1
        ORDER BY subscribers DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Инициализация при импорте
init_db()
