users = [
    {"name": "Ruslan", "age": 26, "city": "Lublin"},
    {"name": "Tonni", "age": 23, "city": "Kiev"},
    {"name": "Simon", "age": 2, "city": "-"}
]

for user in users:
    print(f"{user['name']} ({user['age']}) lives in {user['city']}"),
    if user["city"] == "-": print("has no city specified")