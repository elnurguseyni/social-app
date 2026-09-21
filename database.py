import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash
from flask import current_app, has_app_context


DATABASE = Path(__file__).with_name("social.db")

def get_connection():
    if has_app_context():
        database_url = current_app.config["DATABASE_URL"]
    else:
        database_url = os.environ["DATABASE_URL"]

    return psycopg.connect(
        database_url,
        row_factory=dict_row,
    )

def add_post(content, user_id):
    connection = get_connection()

    row = connection.execute(
        """
        INSERT INTO posts (content, user_id)
        VALUES (%s, %s)
        RETURNING id
        """,
        (content, user_id),
    ).fetchone()

    connection.commit()
    connection.close()

    return row["id"]

def get_posts(user_id=None):
    connection = get_connection()

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
                AND user_like.user_id = %s
            ) AS is_liked
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN likes ON posts.id = likes.post_id
        GROUP BY posts.id, posts.content, users.username
        ORDER BY posts.id
        """,
        (user_id,),
    ).fetchall()

    connection.close()
    return posts

def get_users():
    connection = get_connection()

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
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (username, email, password_hash),
        )

        connection.commit()
        return cursor.fetchone()["id"]
    finally:
        connection.close()

def get_user_by_email(email):
    connection = get_connection()

    user = connection.execute(
        "SELECT id, username, email, password_hash FROM users WHERE email = %s",
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
        INSERT INTO likes (user_id, post_id)
        VALUES (%s, %s)
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
        WHERE user_id = %s AND post_id = %s
        """,
        (user_id, post_id),
    )

    connection.commit()
    connection.close()

def get_like_count(post_id):
    connection = get_connection()

    count = connection.execute(
        "SELECT COUNT(*) FROM likes WHERE post_id = %s",
        (post_id,),
    ).fetchone()[0]

    connection.close()
    return count

def migrate_comments_table():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (content, user_id, post_id),
    )

    comment_id = cursor.fetchone()["id"]
    connection.commit()
    connection.close()

    return comment_id

def get_comments(post_id):
    connection = get_connection()

    comments = connection.execute(
        """
        SELECT comments.content, users.username
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.post_id = %s
        ORDER BY comments.created_at
        """,
        (post_id,),
    ).fetchall()

    connection.close()
    return comments

def initialize_database():
    connection = get_connection()

    schema = Path(__file__).with_name("schema.sql").read_text()
    connection.execute(schema)
    connection.commit()
    connection.close()

def get_or_create_user(username):
    connection = get_connection()

    row = connection.execute(
        "SELECT id FROM users WHERE username = %s",
        (username,),
    ).fetchone()

    if row is not None:
        connection.close()
        return row["id"]

    row = connection.execute(
        """
        INSERT INTO users (username, email, password_hash)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (username, f"{username}@example.com", "temporary-password-hash"),
    ).fetchone()

    connection.commit()
    connection.close()

    return row["id"]


if __name__ == "__main__":
    initialize_database()
    migrate_users_table()
    migrate_likes_table()
    migrate_comments_table()