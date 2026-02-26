from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


# -------------------- Lifespan --------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at application startup.
    # Reads the module-level `engine` at call time, so tests can patch it
    # to SQLite before the first client is created.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)


# -------------------- DB Model --------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)


# -------------------- Pydantic Schema --------------------

class UserCreate(BaseModel):
    name: str
    email: str


# -------------------- Dependency --------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- Routes --------------------

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
