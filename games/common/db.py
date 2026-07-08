"""
MongoDB Connection
---------------------
Single shared Mongo connection for the desktop app's login/registration.
Uses the exact same connection string and collections as the game backend
scripts (e.g. the Bloom Forest controller), so the app and the games all
read/write the same `users` and `sessions` data.
"""

from pymongo import MongoClient

# Copied verbatim from the game backend - keep this in sync if the real
# connection string (with credentials) changes.
uri = "mongodb+srv://@rehabverse.tlpbjja.mongodb.net/?appName=RehabVerse"

client = MongoClient(uri)
db = client["RehabVerse"]
users = db["users"]
sessions = db["sessions"]