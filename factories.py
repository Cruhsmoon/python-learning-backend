from faker import Faker
import random

fake = Faker("uk_UA")


def user_factory():
    return {
        "name": fake.name(),
        "email": fake.unique.email(),
    }


def product_factory():
    return {
        "title": fake.word().capitalize(),
        "price": round(random.uniform(10, 5000), 2),
    }


def order_factory(user_id: int, product_id: int):
    return {
        "user_id": user_id,
        "product_id": product_id,
        "quantity": random.randint(1, 5),
    }