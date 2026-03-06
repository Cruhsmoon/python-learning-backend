from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

# -------------------- JWT Config --------------------

SECRET_KEY = "test-secret-key-do-not-use-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# In-memory user store (auth only — no DB dependency)
USERS_DB = {
    "testuser": {"id": 1, "username": "testuser", "password": "testpass", "role": "user"},
    "admin":    {"id": 2, "username": "admin",    "password": "adminpass", "role": "admin"},
}


# -------------------- Lifespan --------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)


# -------------------- DB Model --------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)


# -------------------- Pydantic Schemas --------------------

class UserCreate(BaseModel):
    name: str
    email: str


class LoginRequest(BaseModel):
    username: str
    password: str


# -------------------- DB Dependency --------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- JWT Helpers --------------------

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    username = payload.get("sub")
    if username not in USERS_DB:
        raise HTTPException(status_code=401, detail="User not found")
    return USERS_DB[username]


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# -------------------- Auth Routes --------------------

@app.post("/auth/login")
def login(credentials: LoginRequest):
    user = USERS_DB.get(credentials.username)
    if not user or user["password"] != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": credentials.username, "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/users/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"],
    }


@app.get("/admin/users")
def admin_list_users(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).all()


# -------------------- User Routes --------------------

@app.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(name=user.name, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
