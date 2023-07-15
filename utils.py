from pydantic import BaseModel
from  typing import AnyStr
from mento import Mento, PrimaryKey
from mento.connection import MentoConnection
from models import LogInModel, UserModel
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse
from asyncio import sleep
from re import search
from datetime import datetime
from enum import Enum, auto

import fastapi

class APIError(Enum):
    NoHashFound = auto()

class FastAPIResponse(fastapi.responses.Response):
    __doc__ = "Belongs to any http FastAPI response"

class FastAttrs(fastapi.FastAPI):
    templates: Jinja2Templates
    db: "Database"

class APISession(dict):
    __doc__ = "Belongs to current user session on browser"


def new_template(app: FastAPI | FastAttrs, name: str, context: dict, status_code: int = 200) -> _TemplateResponse:
    return app.templates.TemplateResponse(name=name, context=context, status_code=status_code)


def generate_username(data: dict) -> AnyStr:
        username_match = search("(.+)\@", data.get("email", str()))
        if username_match:
            return username_match.group().lower()
        else:
            return data.get("hash")

async def add_new_user(app: FastAPI | FastAttrs, request: Request, data: dict) -> APISession:   
    if data:
        userid = id(data)
        email = data["email"]
        username = await generate_username(data=data)
        data.update(dict(email=email, user_id=userid, username=username, register_date_unix=int(datetime.now().timestamp())), hash=hash(userid))
        login = LogIn(**data)
        

        app.db.add("users", data=login.dict())

        request.session["hash"] = login.hash
        request.session["ts"] = login.register_date_unix
        request.session["lifetime"] = 0
        request.session["ending"] = (request.session["ts"] + request.session["lifetime"])
    return request.session


async def login_response(app: FastAPI | FastAttrs, request: Request, form: dict) -> FastAPIResponse | _TemplateResponse:
        if request.session.get("password"):
            return dict(code="200", message="Account exists", data=request.session)
        if form:
            if not form.get("remember_me"):
                form.update(dict(remember_me="off"))
            
            model = UserModel(**form)
            data = app.db.get("users", where=dict(email=model.email, password=model.password))
            if data:
                if request.session.get("hash"):
                    if request.session.get("hash") == data.hash:
                        lifetime = (14 * 86400) if model.remember_me == "on" else 86400
                        ts = data.register_date_unix
                        request.session.update(dict(lifetime=lifetime, ts=ts, ending=(lifetime + ts)))
                        
                        await sleep(1)
                        return RedirectResponse("/")
                    else:
                        request.session.clear()
                        return RedirectResponse(request.base_url)
                else:
                    request.session["hash"] = data.hash
                    request.session["ts"] = int(datetime.now().timestamp())
                    request.session["lifetime"] = (14 * 86400) if model.remember_me == "on" else 86400
                    request.session["ending"] = (request.session["ts"] + request.session["lifetime"])

                    return RedirectResponse("/")
        return app.templates.TemplateResponse("login.html", context=dict(request=request, base=request.base_url))


async def hash_checker(app: FastAPI | FastAttrs, request: Request) -> FastAPIResponse | APIError:
    if request.session.get("hash"):
        user: LogIn = app.db.get("users", where=dict(hash=request.session.get("hash")))
        if request.session.get("hash") == user.hash:
            if request.session.get("ending") > int(datetime.now().timestamp()):
                await sleep(1)
                return RedirectResponse("/")
        else:
            request.session.clear()
            return RedirectResponse(request.url)
    else:
        return APIError.NoHashFound

class LogIn(BaseModel):
    user_id: int
    username: PrimaryKey(str)
    first_name: str
    last_name: str
    email: str
    password: str
    hash: str
    register_date_unix: int

class Database(Mento):
    def __init__(self, connection: MentoConnection = MentoConnection(), default_table: str = None, check_model: BaseModel = None, error_logging: bool = False):
        super().__init__(connection, default_table, check_model, error_logging)
        self.db("users", LogInModel)
    
    def db(self, table: str, model: BaseModel):
        self.model = model
        return self.create(table=table, model=model, unique_columns=["username", "hash"])
    
    def add(self, table: str, data: dict):
        return self.insert(table, data, check_model=self.__getattribute__("model") if hasattr(self, "model") else None)
    
    def get(self, table: str, where: dict = None, first: bool = True):
        res = list(map(lambda kw: LogIn(**kw), self.select(table, where=where)))
        if not res:
            return
        if first:
            res = res[0]
        return res
    def __repr__(self):
        return "<Mento version=1.2>"


class texts(str):
    reset_password_notify = \
    """
            <body>
            <script type="text/javascript">
            alert("Reset mail sent to %s");
            window.location.href = "/login";
            </script>
            </body>
    """