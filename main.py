import os

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import sqlite3
from fastapi.templating import Jinja2Templates
#use of sqlalchemy
'''
seperate function for role base
authorization function
'''
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-me"))

templates = Jinja2Templates(directory="templates")

@app.get('/', response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
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
        )
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, password)
    )
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
    request.session["user"] = username
    return RedirectResponse(
        url="/",
        status_code=303
    )

@app.get('/logout')
async def logout_r(request: Request):
    request.session.clear()
    return RedirectResponse(
        url='/',
        status_code=303
    )