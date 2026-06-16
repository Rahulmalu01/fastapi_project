import os #to interact with environment variable (not necessary tbh)
import sqlite3 #sqllite database
import shutil #handle file uploads
from datetime import datetime #date/timestamp for articles
from pathlib import Path #handle modern file path

from fastapi import FastAPI, Form, Request, UploadFile, File #form - handle form data, Request - handle incoming request, UploadFile and File - handle file uploads
from fastapi.responses import HTMLResponse, RedirectResponse #html response and redirect response for navigation
from fastapi.templating import Jinja2Templates #to render html templates with dynamic data
from fastapi.staticfiles import StaticFiles #handle static files in our project (css in this case)
from starlette.middleware.sessions import SessionMiddleware #handles user sessions for login/logout functionality

BASE_DIR = Path(__file__).resolve().parent #base project dir
DB_PATH = BASE_DIR / "users.db" #database file path

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-me")) #acts as a protection between routes, secret key - cookie sigining
templates = Jinja2Templates(directory=str(BASE_DIR / "templates")) #render html templates from the templates directory
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static") #mount static files (css, js, images) to the /static route


def get_db_connection():
    connection = sqlite3.connect(str(DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection #helper function


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
    ) #database initialization, creates users and posts tables if they don't exist
        #cursor - it is a control structure object used to interact with database, execute queries and fetch results
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
            (
                "Why Quiet Work Matters",
                "A deep dive into focus, rituals, and modern productivity.",
                "The best work is often done in silence, when your mind is clear and the world is far away...",
                "editor",
                datetime.utcnow().strftime("%b %d, %Y"),
                "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=1200&q=80",
            ),
            (
                "Trailblazers and Tiny Wins",
                "The hidden progress behind every success story.",
                "Success rarely arrives overnight. It arrives in the quiet steps that no one sees...",
                "editor",
                datetime.utcnow().strftime("%b %d, %Y"),
                "https://images.unsplash.com/photo-1493815793585-4b1a17b3f4c9?w=1200&q=80",
            ),
            (
                "The Art of Starting Again",
                "Why every reset is also an opportunity.",
                "Sometimes the most important choice is not to continue, but to begin again with wiser eyes...",
                "editor",
                datetime.utcnow().strftime("%b %d, %Y"),
                "https://images.unsplash.com/photo-1487014679447-9f8336841d58?w=1200&q=80",
            ),
            (
                "Stories That Stay With You",
                "What happens when a narrative becomes part of who you are?",
                "Great stories don’t just entertain. They linger, change us, and invite us to imagine a different path...",
                "editor",
                datetime.utcnow().strftime("%b %d, %Y"),
                "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=1200&q=80",
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


def fetch_users():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, username FROM users ORDER BY id ASC")
    users = [dict(row) for row in cursor.fetchall()]
    connection.close()
    return users


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
        # stream the upload to disk to avoid loading whole file into memory
        try:
            image.file.seek(0)
        except Exception:
            pass
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
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
        try:
            image.file.seek(0)
        except Exception:
            pass
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
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


@app.get("/db_route", response_class=HTMLResponse)
async def db_route(request: Request):
    users = fetch_users()
    posts = fetch_posts()
    return render_template(
        request,
        "db_view.html",
        {
            "users": users,
            "posts": posts,
        },
    )