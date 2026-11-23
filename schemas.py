from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=64)

class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: str
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool = False
    priority: int = Field(default=1, ge=1, le=5)

class TaskUpdate(TaskCreate):
    pass

class TaskRead(TaskCreate):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)