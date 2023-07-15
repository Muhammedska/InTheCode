from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from mento import PrimaryKey, UniqueMatch

class UserModel(BaseModel):
    email: str
    password: str
    remember_me: str = "off"

@dataclass
class LogInModel(BaseModel):
    user_id: int
    username: PrimaryKey(str)
    first_name: str
    last_name: str
    email: str
    password: str
    hash: str
    register_date_unix: int

    check_match: UniqueMatch("username", "user_id")
