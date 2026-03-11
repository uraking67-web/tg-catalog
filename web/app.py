import os
from math import ceil

from flask import Flask, abort, render_template, request
from dotenv import load_dotenv

from database import get_channel_by_username, get_db, init_db

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "web", "static")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

PER_PAGE = 24


def fetch_scalar(query: str, params: tuple = ()) -> int:
    conn = get_db()
    try:
        row = conn.execute(query, params).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def fetch_all(query: str, params: tuple = ()) -> list:
    conn = get_db()
    try:
        rows = conn.execute(query, params).fetchall()
        return rows
    finally:
        conn.close()


@app.route("/")
def index():
    total_channels = fetch_scalar("SELECT COUNT(*) FROM channels")
    total_orgs = fetch_scalar("SELECT COUNT(*) FROM channels WHERE is_organization = 1")
    total_categories = fetch_scalar(
        "SELECT COUNT(DISTINCT category) FROM channels WHERE category IS NOT NULL AND TRIM(category) != ''"
    )

    top_categories = fetch_all(
        """
        SELECT
            COALESCE(NULLIF(TRIM(category), ''), 'Без категории') AS category_name,
            COUNT(*) AS cnt
        FROM channels
        WHERE is_organization = 1
        GROUP BY category_name
        ORDER BY cnt DESC, category_name ASC
        LIMIT 12
        """
    )

    latest_channels = fetch_all(
        """
        SELECT username, title, description, subscribers, category
        FROM channels
        WHERE is_organization = 1
        ORDER BY id DESC
        LIMIT 12
        """
    )

    stats = {
        "total_channels": total_channels,
        "organizations": total_orgs,
        "categories": total_categories,
    }

    return render_template(
        "index.html",
        stats=stats,
        total_channels=total_channels,
        total_orgs=total_orgs,
        total_categories=total_categories,
        top_categories=top_categories,
        latest_channels=latest_channels,
    )


@app.route("/catalog")
def catalog():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    page = max(request.args.get("page", default=1, type=int), 1)

    where = ["is_organization = 1"]
    params = []

    if search:
        where.append("(title LIKE ? OR username LIKE ? OR description LIKE ?)")
        search_like = f"%{search}%"
        params.extend([search_like, search_like, search_like])

    if category:
        where.append("category = ?")
        params.append(category)

    where_sql = " AND ".join(where)

    total = fetch_scalar(f"SELECT COUNT(*) FROM channels WHERE {where_sql}", tuple(params))
    total_pages = max(ceil(total / PER_PAGE), 1)
    page = min(page, total_pages)
    offset = (page - 1) * PER_PAGE

    rows = fetch_all(
        f"""
        SELECT username, title, description, subscribers, category
        FROM channels
        WHERE {where_sql}
        ORDER BY subscribers DESC, title ASC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [PER_PAGE, offset]),
    )

    categories = fetch_all(
        """
        SELECT DISTINCT category
        FROM channels
        WHERE is_organization = 1
          AND category IS NOT NULL
          AND TRIM(category) != ''
        ORDER BY category ASC
        """
    )

    return render_template(
        "catalog.html",
        channels=rows,
        categories=[row[0] for row in categories],
        current_category=category,
        q=search,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@app.route("/channel/<username>")
def channel_page(username: str):
    channel = get_channel_by_username(username)
    if not channel:
        abort(404)
    return render_template("channel.html", channel=channel)


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)