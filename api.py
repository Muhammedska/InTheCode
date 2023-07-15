from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from utils import Database, APIError, FastAttrs
import utils

app: FastAPI | FastAttrs = FastAPI()
templates = Jinja2Templates("templates")

app.db = db = Database()
app.templates = templates
app.add_middleware(
    middleware_class=SessionMiddleware,
    secret_key="InTheCodes"
)


@app.get("/")
@app.post("/")
async def index(request: Request, response: Response):
    return utils.new_template(app=app, name="index.html", context=dict(request=request))

@app.get("/getFile")
async def get_file(path: str = None, request: Request = None, response: Response = None):
    return FileResponse(Path("templates") / path)

@app.get("/accounts/password-reset")
async def password_reset(request: Request, response: Response, email: str = None, body: str = str()):
    if email:
        body += utils.texts.reset_password_notify % (email)
        return HTMLResponse(body)
    return utils.new_template(app=app, name="forgot-password.html", context=dict(request=request, base=request.base_url))

@app.get("/register")
@app.post("/user/register")
async def register(request: Request, response: Response):
    data: dict = dict(await request.form())
    hash_check = await utils.hash_checker(app=app, request=request)
    
    if not hash_check == APIError.NoHashFound:
        return hash_check
    
    await utils.add_new_user(app=app, request=request, data=data)
    return templates.TemplateResponse("register.html", context=dict(request=request, base=request.base_url))

@app.get("/login")
@app.post("/user/login")
async def login(request: Request = None, response: Response = None):
    hash_check = await utils.hash_checker(app=app, request=request)
    form = dict(await request.form())

    if not hash_check == APIError.NoHashFound:
        return hash_check
    return await utils.login_response(app=app, request=request, form=form)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")