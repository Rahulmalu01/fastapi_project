import os
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-me"))
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def get_db_connection():
    connection = sqlite3.connect(str(DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            body TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT NOT NULL,
            image_url TEXT
        )
        """
    )
    # ensure legacy tables add image_url when migrating from older versions
    try:
        cursor.execute("ALTER TABLE posts ADD COLUMN image_url TEXT")
    except Exception:
        # column probably already exists
        pass
    connection.commit()
    connection.close()


@app.on_event("startup")
def on_startup():
    init_db()
    # seed a few example posts with images for demos
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM posts")
    count = cursor.fetchone()[0]
    if count == 0:
        sample = [
            (
                "A Quiet Morning in the City",
                "How small rituals can change your day.",
                "It was a quiet morning when the idea first came to him...",
                "editor",
                datetime.utcnow().strftime("%b %d, %Y"),
                "https://images.unsplash.com/photo-1502082553048-f009c37129b9?w=1200&q=80",
            ),
            (
                "On Building Things People Love",
                "A short reflection on product and craft.",
                "We build to solve problems, and sometimes the problems change us...",
                "editor",
                datetime.utcnow().strftime("%b %d, %Y"),
                "https://images.unsplash.com/photo-1506765515384-028b60a970df?w=1200&q=80",
            ),
        ]
        for t, s, b, a, c, img in sample:
            cursor.execute(
                "INSERT INTO posts (title, summary, body, author, created_at, image_url) VALUES (?, ?, ?, ?, ?, ?)",
                (t, s, b, a, c, img),
            )
        connection.commit()
    connection.close()


def get_current_user(request: Request):
    username = request.session.get("user")
    if not username:
        return None

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, username FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    connection.close()
    return dict(user) if user else None


def fetch_posts(limit: int | None = None, author: str | None = None):
    connection = get_db_connection()
    cursor = connection.cursor()
    query = "SELECT * FROM posts"
    parameters: list[object] = []

    if author:
        query += " WHERE author = ?"
        parameters.append(author)

    query += " ORDER BY id DESC"

    if limit is not None:
        query += " LIMIT ?"
        parameters.append(limit)

    cursor.execute(query, parameters)
    posts = [dict(row) for row in cursor.fetchall()]
    connection.close()
    return posts


def fetch_post(post_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    connection.close()
    return dict(post) if post else None


def render_template(request: Request, name: str, context: dict | None = None):
    payload = {"request": request, "user": get_current_user(request)}
    if context:
        payload.update(context)
    return templates.TemplateResponse(request=request, name=name, context=payload)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    posts = fetch_posts(limit=4)
    featured_post = posts[0] if posts else None
    recent_posts = posts[1:] if len(posts) > 1 else []
    return render_template(
        request,
        "home.html",
        {
            "posts": posts,
            "featured_post": featured_post,
            "recent_posts": recent_posts,
        },
    )


@app.get("/signin", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
async def signin_form(request: Request):
    return render_template(request, "signinpage.html", {"message": "", "next_url": request.query_params.get("next", "/")})


@app.post("/signin", response_class=HTMLResponse)
@app.post("/login", response_class=HTMLResponse)
async def signin(request: Request, username: str = Form(...), password: str = Form(...)):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    connection.close()

    if not user:
        return render_template(request, "signinpage.html", {"message": "User not found!"})

    if user["password"] != password:
        return render_template(request, "signinpage.html", {"message": "Invalid password!"})

    request.session["user"] = user["username"]
    return RedirectResponse(url="/", status_code=303)


@app.get("/signup", response_class=HTMLResponse)
async def signup_form(request: Request):
    return render_template(request, "signuppage.html", {"message": ""})


@app.post("/signup", response_class=HTMLResponse)
async def signup(request: Request, username: str = Form(...), password: str = Form(...)):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        connection.close()
        return render_template(request, "signuppage.html", {"message": "Username already exists!"})

    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    connection.commit()
    connection.close()

    request.session["user"] = username
    return RedirectResponse(url="/", status_code=303)


@app.get("/publish", response_class=HTMLResponse)
@app.get("/new", response_class=HTMLResponse)
async def publish_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/signin?next=/publish", status_code=303)
    return render_template(request, "publisharticle.html", {"message": "", "form_data": {"title": "", "summary": "", "body": ""}})


@app.post("/publish", response_class=HTMLResponse)
@app.post("/new", response_class=HTMLResponse)
async def publish_article(
    request: Request,
    title: str = Form(...),
    summary: str = Form(""),
    body: str = Form(...),
    image: UploadFile | None = File(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/signin?next=/publish", status_code=303)

    clean_summary = summary.strip() or body.strip().split("\n", 1)[0][:180]
    created_at = datetime.utcnow().strftime("%b %d, %Y")
    image_url = None
    # handle file upload
    if image and image.filename:
        uploads_dir = BASE_DIR / "static" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{int(datetime.utcnow().timestamp())}_{image.filename.replace(' ', '_')}"
        dest_path = uploads_dir / safe_name
        with open(dest_path, "wb") as f:
            f.write(await image.read())
        image_url = f"/static/uploads/{safe_name}"

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO posts (title, summary, body, author, created_at, image_url) VALUES (?, ?, ?, ?, ?, ?)",
        (title.strip(), clean_summary, body.strip(), user["username"], created_at, image_url),
    )
    connection.commit()
    article_id = cursor.lastrowid
    connection.close()

    return RedirectResponse(url=f"/article/{article_id}", status_code=303)


@app.get("/articles", response_class=HTMLResponse)
@app.get("/toggleexistingarticle", response_class=HTMLResponse)
async def articles(request: Request):
    user = get_current_user(request)
    view = request.query_params.get("view", "all")
    author = user["username"] if view == "mine" and user else None
    posts = fetch_posts(author=author)
    return render_template(
        request,
        "toggleexistingarticle.html",
        {
            "posts": posts,
            "view": view if view == "mine" else "all",
        },
    )


@app.get("/article/{post_id}/edit", response_class=HTMLResponse)
async def edit_article_form(request: Request, post_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url=f"/signin?next=/article/{post_id}/edit", status_code=303)

    post = fetch_post(post_id)
    if not post:
        return RedirectResponse(url="/articles", status_code=303)

    if post["author"] != user["username"]:
        return RedirectResponse(url=f"/article/{post_id}", status_code=303)

    form_data = {"id": post["id"], "title": post["title"], "summary": post["summary"], "body": post["body"], "image_url": post.get("image_url")}
    return render_template(request, "publisharticle.html", {"message": "", "form_data": form_data, "edit_mode": True, "action": f"/article/{post_id}/edit"})


@app.post("/article/{post_id}/edit", response_class=HTMLResponse)
async def edit_article(request: Request, post_id: int, title: str = Form(...), summary: str = Form(""), body: str = Form(...), image: UploadFile | None = File(None)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url=f"/signin?next=/article/{post_id}/edit", status_code=303)

    post = fetch_post(post_id)
    if not post:
        return RedirectResponse(url="/articles", status_code=303)

    if post["author"] != user["username"]:
        return RedirectResponse(url=f"/article/{post_id}", status_code=303)

    image_url = post.get("image_url")
    if image and image.filename:
        uploads_dir = BASE_DIR / "static" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{int(datetime.utcnow().timestamp())}_{image.filename.replace(' ', '_')}"
        dest_path = uploads_dir / safe_name
        with open(dest_path, "wb") as f:
            f.write(await image.read())
        image_url = f"/static/uploads/{safe_name}"

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE posts SET title = ?, summary = ?, body = ?, image_url = ? WHERE id = ?",
        (title.strip(), summary.strip(), body.strip(), image_url, post_id),
    )
    connection.commit()
    connection.close()

    return RedirectResponse(url=f"/article/{post_id}", status_code=303)


@app.get("/article/{post_id}", response_class=HTMLResponse)
@app.get("/post/{post_id}", response_class=HTMLResponse)
async def read_article(request: Request, post_id: int):
    post = fetch_post(post_id)
    if not post:
        return RedirectResponse(url="/articles", status_code=303)

    paragraphs = [segment.strip() for segment in post["body"].split("\n\n") if segment.strip()]
    related_posts = [item for item in fetch_posts(limit=4) if item["id"] != post_id][:3]
    return render_template(
        request,
        "articleread.html",
        {
            "article": post,
            "paragraphs": paragraphs,
            "related_posts": related_posts,
        },
    )


@app.get("/logout")
async def logout_r(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)