import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "catalog.db"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH)))

CATEGORIES = [
    "Бизнес и финансы",
    "IT и технологии",
    "Медиа и СМИ",
    "Образование",
    "Медицина",
    "Ритейл и e-commerce",
    "Государственные организации",
    "Производство",
    "Логистика и транспорт",
    "Недвижимость",
    "Маркетинг и PR",
    "Другое",
]


def ensure_db_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                title TEXT,
                description TEXT,
                subscribers INTEGER DEFAULT 0,
                category TEXT,
                source TEXT,
                found_via TEXT,
                is_organization INTEGER DEFAULT 0,
                reviewed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_channels_username
            ON channels(username)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_channels_category
            ON channels(category)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_channels_is_org
            ON channels(is_organization)
            """
        )

        conn.commit()
    finally:
        conn.close()


def normalize_username(username: str) -> str:
    username = (username or "").strip()
    username = username.removeprefix("https://t.me/")
    username = username.removeprefix("http://t.me/")
    username = username.removeprefix("@")
    return username.strip("/ ").lower()


def upsert_channel(channel: Dict[str, Any]) -> None:
    username = normalize_username(channel.get("username", ""))
    if not username:
        return

    title = (channel.get("title") or "").strip()
    description = (channel.get("description") or "").strip()
    subscribers = int(channel.get("subscribers") or 0)
    category = (channel.get("category") or "").strip()
    source = (channel.get("source") or "").strip()
    found_via = (channel.get("found_via") or "").strip()
    is_organization = int(channel.get("is_organization") or 0)
    reviewed = int(channel.get("reviewed") or 0)

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM channels WHERE username = ?",
            (username,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE channels
                SET
                    title = ?,
                    description = ?,
                    subscribers = ?,
                    category = ?,
                    source = ?,
                    found_via = ?,
                    is_organization = ?,
                    reviewed = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
                """,
                (
                    title,
                    description,
                    subscribers,
                    category,
                    source,
                    found_via,
                    is_organization,
                    reviewed,
                    username,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO channels (
                    username, title, description, subscribers,
                    category, source, found_via, is_organization, reviewed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    title,
                    description,
                    subscribers,
                    category,
                    source,
                    found_via,
                    is_organization,
                    reviewed,
                ),
            )

        conn.commit()
    finally:
        conn.close()


def get_channel_by_username(username: str) -> Optional[Dict[str, Any]]:
    username = normalize_username(username)
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM channels WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def search_channels(query: str = "", category: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db()
    try:
        where = ["is_organization = 1"]
        params: List[Any] = []

        query = (query or "").strip()
        category = (category or "").strip()

        if query:
            like = f"%{query}%"
            where.append("(title LIKE ? OR username LIKE ? OR description LIKE ?)")
            params.extend([like, like, like])

        if category:
            where.append("category = ?")
            params.append(category)

        where_sql = " AND ".join(where)

        rows = conn.execute(
            f"""
            SELECT *
            FROM channels
            WHERE {where_sql}
            ORDER BY subscribers DESC, title ASC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_top_channels(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM channels
            WHERE is_organization = 1
            ORDER BY subscribers DESC, title ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_stats() -> Dict[str, Any]:
    conn = get_db()
    try:
        total_channels = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        total_orgs = conn.execute(
            "SELECT COUNT(*) FROM channels WHERE is_organization = 1"
        ).fetchone()[0]
        total_categories = conn.execute(
            """
            SELECT COUNT(DISTINCT category)
            FROM channels
            WHERE category IS NOT NULL AND TRIM(category) != ''
            """
        ).fetchone()[0]

        top_categories = conn.execute(
            """
            SELECT
                COALESCE(NULLIF(TRIM(category), ''), 'Без категории') AS category_name,
                COUNT(*) AS cnt
            FROM channels
            WHERE is_organization = 1
            GROUP BY category_name
            ORDER BY cnt DESC, category_name ASC
            LIMIT 10
            """
        ).fetchall()

        return {
            "total_channels": total_channels,
            "organizations": total_orgs,
            "categories": total_categories,
            "top_categories": [dict(row) for row in top_categories],
        }
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"✅ База инициализирована: {DB_PATH}")