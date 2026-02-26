import httpx

from fastapi_app.main import User


# ---------- External HTTP ----------

async def get_external_data() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()


async def fetch_github_user(username: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/users/{username}")
        response.raise_for_status()
        return response.json()


# ---------- Database ----------

def create_user(db, name: str, email: str):
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    return user


def save_user(db, name: str, email: str):
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------- Redis ----------

def get_cached_user(redis_client, user_id: int):
    return redis_client.get(f"user:{user_id}")


def cache_user(redis_client, key, data: str) -> None:
    redis_client.set(key, data)
