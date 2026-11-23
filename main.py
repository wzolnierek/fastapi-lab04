from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import logging
import os
import time
from contextlib import asynccontextmanager

from auth import create_access_token, get_current_user, hash_password, verify_password
from database import get_db
from models import Task, User
from schemas import TaskCreate, TaskRead, TaskUpdate, Token, UserRead, UserRegister

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API starting (log level %s)", LOG_LEVEL)
    yield
    logger.info("API shutting down")


app = FastAPI(title="Lab 04 - Wdrozenie", version="4.0", lifespan=lifespan)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    # tylko metoda, sciezka, status i czas - bez naglowkow, hasel i tokenow
    logger.info("%s %s -> %s %.1fms", request.method, request.url.path, response.status_code, ms)
    return response

def get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def require_task_owner(task: Task, current_user: User) -> None:
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to access this task")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status_code=409, detail="User with this email already exists")
    user = User(email=data.email, name=data.name, hashed_password=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User with this email already exists")
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username))
    if (
        user is None
        or user.hashed_password is None
        or not verify_password(form.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(user.email), "token_type": "bearer"}


@app.get("/users/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    task = Task(**data.model_dump(), user_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=list[TaskRead])
def list_tasks(
    completed: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Task).where(Task.user_id == current_user.id).order_by(Task.id)
    if completed is not None:
        stmt = stmt.where(Task.completed == completed)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all()


@app.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    task = get_task_or_404(task_id, db)
    require_task_owner(task, current_user)
    return task


@app.put("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    task = get_task_or_404(task_id, db)
    require_task_owner(task, current_user)
    for field, value in data.model_dump().items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    task = get_task_or_404(task_id, db)
    require_task_owner(task, current_user)
    db.delete(task)
    db.commit()