<<<<<<< HEAD
﻿from datetime import datetime
from pathlib import Path
=======
import os

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
>>>>>>> 1f966aea1c277d80e80e32a1a190353e62247ed3
import sqlite3

from fastapi import FastAPI, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "blog.db"
SECRET_KEY = "replace-this-with-a-long-secret-key"

app = FastAPI()
<<<<<<< HEAD
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
=======
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-me"))
>>>>>>> 1f966aea1c277d80e80e32a1a190353e62247ed3

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

<<<<<<< HEAD
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
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    connection.close()
    if not row:
        return None
    return {"username": row["username"]}


def get_post(post_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None


@app.get("/", response_class=HTMLResponse)
=======
@app.get('/', response_class=HTMLResponse)
>>>>>>> 1f966aea1c277d80e80e32a1a190353e62247ed3
async def home(request: Request):
    user = get_current_user(request)
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = [dict(row) for row in cursor.fetchall()]
    connection.close()
    return templates.TemplateResponse(
<<<<<<< HEAD
        "home.html",
        {"request": request, "posts": posts, "user": user},
    )


@app.get("/signup", response_class=HTMLResponse)
async def signup_form(request: Request):
    return templates.TemplateResponse(
        "signup.html",
        {"request": request, "message": "", "user": get_current_user(request)},
    )


@app.post("/signup", response_class=HTMLResponse)
async def signup(request: Request, username: str = Form(...), password: str = Form(...)):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        connection.close()
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "message": "Username already exists.",
                "user": get_current_user(request),
            },
=======
        request=request,
        name="home.html",
        context={}
    )

@app.get('/signup', response_class=HTMLResponse)
async def signup_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={"message": ""}
    )

@app.post('/signup', response_class=HTMLResponse)
async def signup(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"message": "Username already exists!"}
>>>>>>> 1f966aea1c277d80e80e32a1a190353e62247ed3
        )

    cursor.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, password),
    )
<<<<<<< HEAD
    connection.commit()
    connection.close()
=======
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get('/login', response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"message": ""}
    )

@app.post('/login', response_class=HTMLResponse)
async def login_view(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )
    user = cursor.fetchone()
    conn.close()
    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"message": "User not found!"}
        )
    stored_password = user[2]
    if stored_password != password:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"message": "Invalid password!"}
        )
>>>>>>> 1f966aea1c277d80e80e32a1a190353e62247ed3
    request.session["user"] = username
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "message": "", "user": get_current_user(request)},
    )

<<<<<<< HEAD

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    connection.close()

    if not row or row["password"] != password:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "message": "Invalid username or password.",
                "user": get_current_user(request),
            },
        )

    request.session["user"] = username
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/logout")
async def logout(request: Request):
=======
@app.get('/logout')
async def logout_r(request: Request):
>>>>>>> 1f966aea1c277d80e80e32a1a190353e62247ed3
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/new", response_class=HTMLResponse)
async def new_post_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "new_post.html",
        {"request": request, "user": user},
    )


@app.post("/new", response_class=HTMLResponse)
async def create_post(request: Request, title: str = Form(...), body: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO posts (title, body, author, created_at) VALUES (?, ?, ?, ?)",
        (title, body, user["username"], datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
    )
    connection.commit()
    connection.close()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/post/{post_id}", response_class=HTMLResponse)
async def post_detail(request: Request, post_id: int):
    post = get_post(post_id)
    if not post:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "post_detail.html",
        {"request": request, "post": post, "user": get_current_user(request)},
    )


@app.get("/post/{post_id}/edit", response_class=HTMLResponse)
async def edit_post_form(request: Request, post_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    post = get_post(post_id)
    if not post or post["author"] != user["username"]:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse(
        "edit_post.html",
        {"request": request, "post": post, "user": user},
    )


@app.post("/post/{post_id}/edit", response_class=HTMLResponse)
async def edit_post(request: Request, post_id: int, title: str = Form(...), body: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    post = get_post(post_id)
    if not post or post["author"] != user["username"]:
        raise HTTPException(status_code=404)

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE posts SET title = ?, body = ? WHERE id = ?",
        (title, body, post_id),
    )
    connection.commit()
    connection.close()
    return RedirectResponse(url=f"/post/{post_id}", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/post/{post_id}/delete")
async def delete_post(request: Request, post_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    post = get_post(post_id)
    if not post or post["author"] != user["username"]:
        raise HTTPException(status_code=404)

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    connection.commit()
    connection.close()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "user": get_current_user(request)},
        status_code=404,
    )
