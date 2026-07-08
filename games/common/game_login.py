"""
Game CLI Login
-----------------
Extracted from the Bloom Forest backend, unchanged: interactive
command-line login/registration. Used only when a game controller script
is run standalone (double-clicked / run without an argument), so it still
works exactly like it always did outside the app. The only change from
the original is that it points at the shared `users` collection in db.py
instead of opening its own MongoClient - same database, same URI, same
documents.
"""

from datetime import datetime
import string
import random
from db import users


def generate_user_id(name):
    random_part = ''.join(random.choices(string.digits, k=4))
    return name[:3].upper() + random_part


def login():
    user_id = input("Enter username ID: ").upper()
    password = input("Enter Password: ")

    # check if user exists
    user = users.find_one({"user_id": user_id})

    # CASE 1: user exists → login
    if user:
        print("User found ✔")

        if user["password"] == password:
            print("Login successful ✔")
            return user_id
        else:
            print("Wrong password ❌")
            exit()

    # CASE 2: user does NOT exist → auto register
    else:
        print("New user detected → creating account...")

        name = input("Enter Name: ")

        new_user = {
            "user_id": user_id,
            "name": name,
            "password": password,
            "created_at": datetime.now(),
            "stats": {
                "vines_sessions": 0,
                "neuro sessions":0
            }
        }

        users.insert_one(new_user)

        print("Account created ✔ Welcome", name)

        return user_id