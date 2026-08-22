import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from sqlalchemy import text
from models import db, User
from upload_config import save_uploaded_file
from admin.dashboard import admin_required

user_bp = Blueprint('admin_user', __name__, url_prefix='/admin')

@user_bp.route('/users')
@user_bp.route('/user')
@admin_required
def admin_users():
    try:
        query = text("SELECT * FROM users ORDER BY id DESC")
        result = db.session.execute(query)
        users = [{
            "id": row.id,
            "username": row.username,
            "email": getattr(row, 'email', ''),
            "phone_number": getattr(row, 'phone_number', ''),
            "role": row.role,
            "name": getattr(row, 'name', ''),
            "create_at": row.create_at.strftime("%d %b %Y, %I:%M %p") if getattr(row, 'create_at', None) else '',
            "profile_image": getattr(row, 'profile_image', '') or 'no-profile.png'
        } for row in result]
    except Exception:
        users = [u.to_dict() for u in User.query.order_by(User.id.desc()).all()]

    return render_template('admin/users.html', users=users)

@user_bp.route('/users/<int:user_id>')
@admin_required
def user_details(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_user.admin_users'))
    return render_template('admin/user_detail.html', user=user)

@user_bp.route('/users/add', methods=['GET', 'POST'])
@user_bp.route('/user/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone_number = request.form.get('phone_number', '').strip()
        role = request.form.get('role', 'customer')
        name = request.form.get('name', username).strip()

        if not username or not email or not password:
            flash("Username, email, and password are required.", "danger")
            return redirect(url_for('admin_user.add_user'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or Email already exists.", "danger")
            return redirect(url_for('admin_user.add_user'))

        profile_file = request.files.get('profile')
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        filename = save_uploaded_file(profile_file, upload_folder=upload_folder) or 'no-profile.png'

        new_user = User(
            username=username,
            email=email,
            password=password,
            phone_number=phone_number,
            role=role,
            name=name,
            profile_image=filename
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f"User '{username}' created successfully!", "success")
        return redirect(url_for('admin_user.admin_users'))

    return render_template('admin/user_form.html', edit_mode=False)

@user_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@user_bp.route('/user/edit/<user_identifier>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id=None, user_identifier=None):
    if user_id:
        user = User.query.get(user_id)
    else:
        if str(user_identifier).isdigit():
            user = User.query.get(int(user_identifier))
        else:
            user = User.query.filter_by(username=user_identifier).first()

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_user.admin_users'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        role = request.form.get('role', 'customer')
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()

        if username:
            user.username = username
        if email:
            user.email = email
        if phone_number:
            user.phone_number = phone_number
        if role:
            user.role = role
        if name:
            user.name = name
        if password:
            user.password = password

        try:
            profile_file = request.files.get('profile')
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            filename = save_uploaded_file(profile_file, upload_folder=upload_folder)
            if filename:
                if user.profile_image and user.profile_image != 'no-profile.png':
                    old_path = os.path.join(upload_folder, user.profile_image)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except Exception:
                            pass
                user.profile_image = filename
        except Exception as e:
            print(f"Error updating avatar: {e}")

        db.session.commit()
        flash(f"User '{user.username}' updated successfully!", "success")
        return redirect(url_for('admin_user.admin_users'))

    return render_template('admin/user_form.html',
        edit_mode=True,
        user=user,
        edit_username=user.username,
        user_data=user.to_dict()
    )

@user_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@user_bp.route('/user/delete/<user_identifier>', methods=['POST'])
@admin_required
def delete_user(user_id=None, user_identifier=None):
    if user_id:
        user = User.query.get(user_id)
    else:
        if str(user_identifier).isdigit():
            user = User.query.get(int(user_identifier))
        else:
            user = User.query.filter_by(username=user_identifier).first()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_user.admin_users'))

    if session.get('username') == user.username:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('admin_user.admin_users'))

    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if user.profile_image and user.profile_image != 'no-profile.png':
        old_path = os.path.join(upload_folder, user.profile_image)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' deleted successfully!", "success")
    return redirect(url_for('admin_user.admin_users'))
