import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
from flask import current_app


DATABASE = Path(__file__).with_name("social.db")

def get_connection():
    database_path = current_app.config.get("DATABASE", DATABASE)

    connection = sqlite3.connect(database_path, timeout=5)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def add_post(content, user_id):
    connection = get_connection()

    cursor = connection.execute(
        "INSERT INTO posts (content, user_id) VALUES (?, ?)",
        (content, user_id),
    )

    connection.commit()
    post_id = cursor.lastrowid
    connection.close()

    return post_id

def get_posts():
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    posts = connection.execute(
        """
        SELECT posts.content, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id
        """
    ).fetchall()

    connection.close()
    return posts

def get_users():
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    users = connection.execute(
        "SELECT id, username FROM users ORDER BY username"
    ).fetchall()

    connection.close()
    return users

def migrate_users_table():
    connection = get_connection()

    columns = connection.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    column_names = {column[1] for column in columns}

    if "email" not in column_names:
        connection.execute("ALTER TABLE users ADD COLUMN email TEXT")

    if "password_hash" not in column_names:
        connection.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

    connection.commit()
    connection.close()

def create_user(username, email, password):
    connection = get_connection()

    try:
        password_hash = generate_password_hash(password)

        cursor = connection.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (username, email, password_hash),
        )

        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()

def get_user_by_email(email):
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    user = connection.execute(
        "SELECT id, username, email, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    connection.close()
    return user

def initialize_database():
    connection = get_connection()

    schema = Path(__file__).with_name("schema.sql").read_text()
    connection.executescript(schema)

    connection.close()

def get_or_create_user(username):
    connection = sqlite3.connect(DATABASE)

    row = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if row is not None:
        connection.close()
        return row[0]

    cursor = connection.execute(
        "INSERT INTO users (username) VALUES (?)",
        (username,),
    )


    connection.commit()
    user_id = cursor.lastrowid
    connection.close()

    return user_id

if __name__ == "__main__":
    initialize_database()
    migrate_users_table()

    user_id = get_or_create_user("jordan")
    add_post("My first database-backed post", user_id)

    for post in get_posts():
        print(f"{post['username']}: {post['content']}")

    print(f"Created account with ID {new_user_id}")

    for post in get_posts():
        print(f"{post['username']}: {post['content']}")