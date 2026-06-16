import os
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-me"))
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()


@app.on_event("startup")
def on_startup():
    init_db()


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
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/signin?next=/publish", status_code=303)

    clean_summary = summary.strip() or body.strip().split("\n", 1)[0][:180]
    created_at = datetime.utcnow().strftime("%b %d, %Y")

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO posts (title, summary, body, author, created_at) VALUES (?, ?, ?, ?, ?)",
        (title.strip(), clean_summary, body.strip(), user["username"], created_at),
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