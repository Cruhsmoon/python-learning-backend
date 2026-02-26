import httpx
from sqlalchemy.orm import Session

from fastapi_app.main import User


async def fetch_github_user(username: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/users/{username}")
        response.raise_for_status()
        return response.json()


def save_user(db: Session, name: str, email: str) -> User:
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_cached_user(redis_client, user_id: int):
    return redis_client.get(f"user:{user_id}")


def cache_user(redis_client, user_id: int, data: str) -> None:
    redis_client.set(f"user:{user_id}", data)