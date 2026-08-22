import os
from sqlalchemy import text

from flask import current_app, flash, redirect, render_template, request, url_for, session
from werkzeug.utils import secure_filename

from extensions import db
from models.user import User

from . import admin_bp

# </admin/user>
@admin_bp.route("/user")
def user_index():
    # noinspection SqlNoDataSourceInspection,SqlResolve
    sql = text("SELECT * FROM user")
    result = db.session.execute(sql)
    users = result.mappings().all()

    return render_template("admin/user/index.html", users=users)

# </admin/user/create>
@admin_bp.route("/user/create", methods=["GET", "POST"])
def user_create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        phone_number = request.form.get("phone_number", "").strip()
        role = request.form.get("role", "customer")
        name = request.form.get("name", username).strip()

        # User.query.filter_by call ORM
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists! Please use a different email.", "danger")
            return render_template("admin/user/create.html")

        if User.query.filter_by(username=username).first():
            flash("Username already exists! Please choose a different username.", "danger")
            return render_template("admin/user/create.html")

        if phone_number and User.query.filter_by(phone_number=phone_number).first():
            flash(f"Phone number '{phone_number}' is already registered! Please use a different phone number.", "danger")
            return render_template("admin/user/create.html")

        file = request.files.get("profile")
        profile_path = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            upload_folder = current_app.config["UPLOAD_FOLDER"]

            os.makedirs(upload_folder, exist_ok=True)
            file_save_path = os.path.join(upload_folder, filename)
            file.save(file_save_path)

            profile_path = filename

        # save to db
        new_user = User(
            username=username,
            email=email,
            password=password,
            profile_image=profile_path or "no-profile.png",
            phone_number=phone_number,
            role=role,
            name=name
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("User created successfully!", "success")
        return redirect(url_for("admin.user_index"))

    return render_template("admin/user/create.html")

# </admin/user/edit/<id>>
@admin_bp.route("/user/edit/<int:id>", methods=["GET", "POST"])
def user_edit(id):
    user = User.query.get(id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.user_index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        role = request.form.get("role", "customer")
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")

        if email and email != user.email:
            existing_user = User.query.filter(User.email == email, User.id != user.id).first()
            if existing_user:
                flash("Email already exists! Please use a different email.", "danger")
                return render_template("admin/user/edit.html", user=user, edit_mode=True, edit_username=user.username)
            user.email = email

        if username and username != user.username:
            if User.query.filter(User.username == username, User.id != user.id).first():
                flash("Username already exists! Please choose a different username.", "danger")
                return render_template("admin/user/edit.html", user=user, edit_mode=True, edit_username=user.username)
            user.username = username

        if phone_number:
            existing_phone = User.query.filter(User.phone_number == phone_number, User.id != user.id).first()
            if existing_phone:
                flash(f"Phone number '{phone_number}' is already registered! Please use a different phone number.", "danger")
                return render_template("admin/user/edit.html", user=user, edit_mode=True, edit_username=user.username)
            user.phone_number = phone_number
        elif phone_number == '':
            user.phone_number = ''

        if role:
            user.role = role
        if name:
            user.name = name
        if password:
            user.set_password(password)

        file = request.files.get("profile")
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            upload_folder = current_app.config["UPLOAD_FOLDER"]

            os.makedirs(upload_folder, exist_ok=True)
            file_save_path = os.path.join(upload_folder, filename)
            file.save(file_save_path)

            user.profile_image = filename

        db.session.commit()
        flash("User updated successfully!", "success")
        return redirect(url_for("admin.user_index"))

    return render_template("admin/user/edit.html", user=user, edit_mode=True, edit_username=user.username, user_data=user.to_dict())

# </admin/user/delete/<id>>
@admin_bp.route("/user/delete/<int:id>", methods=["GET", "POST"])
def user_delete(id):
    user = User.query.get(id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.user_index"))

    if request.method == "POST":
        db.session.delete(user)
        db.session.commit()

        flash("User deleted successfully!", "success")
        return redirect(url_for("admin.user_index"))

    return render_template("admin/user/delete.html", user=user)
