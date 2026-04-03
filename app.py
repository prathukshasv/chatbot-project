from __future__ import annotations
import re
import sqlite3
import string
from datetime import datetime
from pathlib import Path

import wikipedia
from flask import Flask, jsonify, redirect, render_template, request, session

app = Flask(__name__)
app.secret_key = "secret123"

DB_PATH = Path(__file__).with_name("users.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# DATABASE INIT
def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


init_db()


def preprocess(text: str) -> str:
    return (text or "").lower().translate(str.maketrans("", "", string.punctuation)).strip()


def wikipedia_topic_from_query(preprocessed: str) -> str:
    """Turn 'what is html' into 'html' so Wikipedia can find the article."""
    s = preprocessed.strip()
    patterns = (
        r"^what is\s+(.+)$",
        r"^what are\s+(.+)$",
        r"^who is\s+(.+)$",
        r"^who are\s+(.+)$",
        r"^define\s+(.+)$",
        r"^explain\s+(.+)$",
        r"^tell me about\s+(.+)$",
    )
    for p in patterns:
        m = re.match(p, s)
        if m:
            return m.group(1).strip()
    return s


def wikipedia_lookup(topic: str) -> str:
    wikipedia.set_lang("en")
    topic = topic.strip()
    if not topic:
        raise ValueError("empty topic")

    # Search first: auto_suggest on short queries like "html" can wrongly pick "HTTP".
    titles = wikipedia.search(topic, results=5) or []
    if titles:
        try:
            return wikipedia.summary(titles[0], sentences=2, auto_suggest=False, redirect=True)
        except wikipedia.exceptions.DisambiguationError as e:
            if e.options:
                return wikipedia.summary(e.options[0], sentences=2, auto_suggest=False, redirect=True)
            raise
        except wikipedia.exceptions.PageError:
            pass

    try:
        return wikipedia.summary(topic, sentences=2, auto_suggest=True, redirect=True)
    except wikipedia.exceptions.DisambiguationError as e:
        if e.options:
            return wikipedia.summary(e.options[0], sentences=2, auto_suggest=False, redirect=True)
        raise
    except wikipedia.exceptions.PageError:
        raise


# CHATBOT
def chatbot_response(user_input: str) -> str:
    user_input = preprocess(user_input)

    if user_input in ["hi", "hello", "hey"]:
        return "Hello! How can I help you?"

    if "how are you" in user_input:
        return "I'm doing great. How can I help you?"

    if "your name" in user_input:
        return "I am ChatMate, your AI assistant."

    if "who are you" in user_input:
        return "I am a chatbot built using Python and NLP."

    if "python" in user_input:
        return "Python is a powerful programming language."

    if "machine learning" in user_input:
        return "Machine Learning is a subset of AI."

    if "ai" in user_input:
        return "Artificial Intelligence enables machines to learn."

    if "time" in user_input:
        return datetime.now().strftime("%H:%M:%S")

    if "bye" in user_input:
        return "Goodbye!"

    topic = wikipedia_topic_from_query(user_input)
    try:
        return wikipedia_lookup(topic)
    except Exception:
        return "Sorry, I couldn't understand that."


def require_user() -> str | None:
    user = session.get("user")
    return user if isinstance(user, str) and user else None


# ROUTES
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        if not username:
            return render_template("login.html", error="Please enter a username.")
        session["user"] = username
        return redirect("/chat")
    return render_template("login.html")


@app.route("/chat")
def chat():
    user = require_user()
    if not user:
        return redirect("/")

    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT message, response FROM chats WHERE user=? ORDER BY id ASC",
            (user,),
        )
        chats = cursor.fetchall()

    return render_template("index.html", chats=chats, user=user)


@app.route("/get", methods=["POST"])
def get_bot_response():
    user = require_user()
    if not user:
        return jsonify({"response": "Please log in again."}), 401

    user_input = request.form.get("msg") or ""
    response = chatbot_response(user_input)

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chats (user, message, response, created_at) VALUES (?, ?, ?, ?)",
            (user, user_input, response, datetime.now().isoformat(timespec="seconds")),
        )

    return jsonify({"response": response})


# DELETE HISTORY
@app.route("/clear")
def clear_chat():
    user = require_user()
    if not user:
        return redirect("/")

    with get_conn() as conn:
        conn.execute("DELETE FROM chats WHERE user=?", (user,))

    return redirect("/chat")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
