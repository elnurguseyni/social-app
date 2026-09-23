from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from database import (
    add_post,
    create_user,
    get_or_create_user,
    get_posts,
    get_user_by_email,
    get_users,
    like_post,
    unlike_post,
    add_comment,
    get_comments,
    get_like_count,
    get_user_profile
)
import sqlite3

def register_routes(app):
    @app.route("/")
    def home():
        users = get_users()
        user_id = session.get("user_id")
        posts = get_posts(user_id)

        comments_by_post = {
            post["id"]: get_comments(post["id"])
            for post in posts
        }
        return render_template(
            "index.html",
            users=users,
            posts=posts,
            comments_by_post=comments_by_post,
        )

    @app.route("/posts/<int:post_id>/comments", methods=["POST"])
    def create_comment(post_id):
        user_id = session.get("user_id")

        if user_id is None:
            return redirect(url_for("login"))

        content = request.form["content"].strip()

        if not content:
            return "Comment content is required", 400

        add_comment(content, user_id, post_id)

        return redirect(url_for("home"))

    @app.route("/posts", methods=["POST"])
    def create_post():
        user_id = session.get("user_id")

        if user_id is None:
            return redirect(url_for("login"))

        content = request.form["content"].strip()

        if not content:
            return "Post content is required", 400

        add_post(content, user_id)

        return redirect(url_for("home"))


    @app.route("/posts/<int:post_id>/like", methods=["POST"])
    def like(post_id):
        user_id = session.get("user_id")

        if user_id is None:
            return redirect(url_for("login"))

        post = get_posts(user_id)
        selected_post = next(
            post for post in post if post["id"] == post_id
        )

        if selected_post["is_liked"]:
            unlike_post(user_id, post_id)
        else:
            like_post(user_id, post_id)

        return redirect(url_for("home"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        error = None

        if request.method == "POST":
            username = request.form["username"].strip()
            email = request.form["email"].strip()
            password = request.form["password"]

            if len(username) < 3:
                error = "Username must be at least 3 characters."
            elif "@" not in email:
                error = "Enter a valid email address."
            elif len(password) < 8:
                error = "Password must be at least 8 characters."
            else:
                try:
                    new_user_id = create_user(username, email, password)
                except sqlite3.IntegrityError:
                    error = "That account already exists."
                else:
                    session["user_id"] = new_user_id
                    return redirect(url_for("home"))

        return render_template("register.html", error=error)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form["email"].strip()
            password = request.form["password"]

            user = get_user_by_email(email)

            if user is not None and check_password_hash(
                user["password_hash"],
                password,
            ):
                session["user_id"] = user["id"]
                return redirect(url_for("home"))

            return "Invalid email or password", 401

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))

    @app.route("/users/<username>")
    def profile(username):
        profile_data = get_user_profile(username)

        if profile_data is None:
            return "User not found", 404

        return render_template(
            "profile.html",
            user=profile_data["user"],
            posts=profile_data["posts"],
        )