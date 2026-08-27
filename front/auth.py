from flask import render_template, request, redirect, url_for, flash, session
from extensions import db
from models.user import User
from . import front_bp

# </front/login>
@front_bp.route("/login", methods=["GET", "POST"])
def login():
    # If user is already logged in, redirect them directly
    if "username" in session:
        logged_in_user = User.query.filter_by(username=session["username"]).first()
        if logged_in_user and logged_in_user.role == "admin":
            return redirect(url_for("admin.user_index"))
        return redirect(url_for("front.home"))

    if request.method == "POST":
        username_or_email = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if user and user.check_password(password):
            session["username"] = user.username
            flash(f"Welcome back, {user.username}!", "success")
            if user.role == "admin":
                return redirect(url_for("admin.user_index"))
            return redirect(url_for("front.home"))

        flash("Invalid username/email or password.", "error")
        return redirect(url_for("front.login"))

    return render_template("share/login.html")

# </front/register>
@front_bp.route("/register", methods=["GET", "POST"])
def register():
    # If user is already logged in, redirect them directly
    if "username" in session:
        logged_in_user = User.query.filter_by(username=session["username"]).first()
        if logged_in_user and logged_in_user.role == "admin":
            return redirect(url_for("admin.user_index"))
        return redirect(url_for("front.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("front.register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("front.register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return redirect(url_for("front.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for("front.register"))

        new_user = User(username=username, email=email, role="customer", name=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        session["username"] = username
        flash("Account created successfully! Welcome to the shop.", "success")
        return redirect(url_for("front.home"))

    return render_template("share/register.html")

# </front/logout>
@front_bp.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have logged out successfully.", "success")
    return redirect(url_for("front.home"))
