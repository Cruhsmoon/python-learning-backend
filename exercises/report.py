import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class User:
    """Represents a user with a name, age, and optional city."""
    name: str
    age: int
    city: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Creates a User instance from a dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            age=data.get("age", 0),
            city=data.get("city")
        )

    def __str__(self) -> str:
        """Returns a formatted string representation of the user."""
        location = f"lives in {self.city}" if self.city else "has no city specified"
        return f"{self.name} ({self.age}) {location}"


def load_users(filename: str) -> Iterable[User]:
    """
    Loads users from a JSON file. Yields User objects.
    """
    path = Path(filename)
    if not path.exists():
        print(f"Error: File '{filename}' not found.", file=sys.stderr)
        return

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            if not isinstance(data, list):
                raise ValueError("JSON structure must be a list.")
            yield from (User.from_dict(user) for user in data)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error processing '{filename}': {e}", file=sys.stderr)


def generate_report(users: Iterable[User]) -> None:
    """Prints a summary report of the users."""
    user_list = list(users)
    if not user_list:
        print("No users found or error loading data.")
        return

    print(f"Total users: {len(user_list)}\n")
    for user in user_list:
        print(user)


def main() -> None:
    """Main entry point."""
    generate_report(load_users("data/users.json"))


if __name__ == "__main__":
    main()
