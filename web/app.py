"""
Сайт-каталог Telegram-каналов организаций
"""

import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from database import (
    get_all_channels, search_channels, get_channels_by_category,
    get_stats, get_top_channels, get_db, CATEGORIES
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = Flask(__name__)
PER_PAGE = 30

ICONS = {
    "IT и технологии": "💻", "Бизнес и финансы": "🏢", "Медиа и СМИ": "📰",
    "Госорганы": "🏛", "Образование": "🎓", "Медицина": "🏥",
    "Ритейл и e-commerce": "🛒", "Промышленность": "🏭",
    "Юридические услуги": "⚖️", "Другое": "🎨",
}


@app.route("/")
def index():
    stats = get_stats()
    top = get_top_channels(10)
    cats = list(CATEGORIES.keys()) + ["Другое"]
    return render_template("index.html", stats=stats, top=top, categories=cats, icons=ICONS)


@app.route("/catalog")
def catalog():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "subscribers")
    category = request.args.get("category", "")
    query = request.args.get("q", "")
    offset = (page - 1) * PER_PAGE

    if query:
        channels = search_channels(query, limit=PER_PAGE, offset=offset)
        conn = get_db()
        total = conn.execute(
            "SELECT COUNT(*) FROM channels WHERE (title LIKE ? OR description LIKE ? OR username LIKE ?) AND is_organization=1",
            (f"%{query}%", f"%{query}%", f"%{query}%")).fetchone()[0]
        conn.close()
    elif category:
        channels = get_channels_by_category(category, limit=PER_PAGE, offset=offset)
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) FROM channels WHERE category=? AND is_organization=1", (category,)).fetchone()[0]
        conn.close()
    else:
        channels = get_all_channels(limit=PER_PAGE, offset=offset, sort=sort)
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) FROM channels WHERE is_organization=1").fetchone()[0]
        conn.close()

    total_pages = math.ceil(total / PER_PAGE) if total else 1
    cats = list(CATEGORIES.keys()) + ["Другое"]
    return render_template("catalog.html", channels=channels, page=page, total_pages=total_pages,
                           total=total, sort=sort, category=category, query=query, categories=cats, icons=ICONS)


@app.route("/channel/<username>")
def channel_detail(username):
    conn = get_db()
    ch = conn.execute("SELECT * FROM channels WHERE username=?", (username,)).fetchone()
    conn.close()
    if not ch:
        return render_template("404.html"), 404
    return render_template("channel.html", channel=dict(ch), icons=ICONS)


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "")
    if len(q) < 2:
        return jsonify([])
    results = search_channels(q, limit=10)
    return jsonify([{"username": r["username"], "title": r["title"],
                     "subscribers": r["subscribers"], "category": r["category"]} for r in results])


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    print(f"🌐 Сайт: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
