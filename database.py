import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
from flask import current_app, has_app_context


DATABASE = Path(__file__).with_name("social.db")

def get_connection():
    if has_app_context():
        database_path = current_app.config.get("DATABASE", DATABASE)
    else:
        database_path = DATABASE

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

def get_posts(user_id=None):
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    posts = connection.execute(
        """
        SELECT
            posts.id,
            posts.content,
            users.username,
            COUNT(likes.post_id) AS like_count,
            EXISTS (
                SELECT 1
                FROM likes user_like
                WHERE user_like.post_id = posts.id
                AND user_like.user_id = ?
            ) AS is_liked
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN likes ON posts.id = likes.post_id
        GROUP BY posts.id
        ORDER BY posts.id
        """,
        (user_id,),
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

def migrate_likes_table():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS likes (
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
        """
    )

    connection.commit()
    connection.close()

def like_post(user_id, post_id):
    connection = get_connection()

    connection.execute(
        """
        INSERT OR IGNORE INTO likes (user_id, post_id)
        VALUES (?, ?)
        """,
        (user_id, post_id),
    )

    connection.commit()
    connection.close()

def unlike_post(user_id, post_id):
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM likes
        WHERE user_id = ? AND post_id = ?
        """,
        (user_id, post_id),
    )

    connection.commit()
    connection.close()

def get_like_count(post_id):
    connection = get_connection()

    count = connection.execute(
        "SELECT COUNT(*) FROM likes WHERE post_id = ?",
        (post_id,),
    ).fetchone()[0]

    connection.close()
    return count

def migrate_comments_table():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
        """
    )

    connection.commit()
    connection.close()

def add_comment(content, user_id, post_id):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO comments (content, user_id, post_id)
        VALUES (?, ?, ?)
        """,
        (content, user_id, post_id),
    )

    connection.commit()
    comment_id = cursor.lastrowid
    connection.close()

    return comment_id

def get_comments(post_id):
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    comments = connection.execute(
        """
        SELECT comments.content, users.username
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.post_id = ?
        ORDER BY comments.created_at
        """,
        (post_id,),
    ).fetchall()

    connection.close()
    return comments

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
    migrate_likes_table()
    migrate_comments_table()