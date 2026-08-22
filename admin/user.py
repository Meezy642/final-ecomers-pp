import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from sqlalchemy import text
from models import db, User
from upload_config import save_uploaded_file
from admin.dashboard import admin_required

user_bp = Blueprint('admin_user', __name__, url_prefix='/admin')

@user_bp.route('/users', endpoint='admin_users')
@user_bp.route('/user', endpoint='admin_users_alt')
@admin_required
def admin_users():
    # Only list customer accounts (exclude system admin)
    user_records = User.query.filter(User.username != 'admin', User.role != 'admin').order_by(User.id.desc()).all()
    users = {u.username: u.to_dict() for u in user_records}
    return render_template('admin/users.html', users=users)

@user_bp.route('/users/<int:user_id>')
@admin_required
def user_details(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_user.admin_users'))
    return render_template('admin/user_detail.html', user=user)

@user_bp.route('/users/add', methods=['GET', 'POST'], endpoint='add_user')
@user_bp.route('/user/add', methods=['GET', 'POST'], endpoint='admin_add_user')
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

        if User.query.filter_by(username=username).first():
            flash(f"Username '{username}' already exists.", "danger")
            return redirect(url_for('admin_user.add_user'))

        if User.query.filter_by(email=email).first():
            flash(f"Email '{email}' is already registered.", "danger")
            return redirect(url_for('admin_user.add_user'))

        if phone_number:
            existing_phone_user = User.query.filter_by(phone_number=phone_number).first()
            if existing_phone_user:
                flash(f"Phone number '{phone_number}' is already registered to user @{existing_phone_user.username}.", "danger")
                return redirect(url_for('admin_user.add_user'))

        profile_file = request.files.get('profile')
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        filename = save_uploaded_file(profile_file, upload_folder=upload_folder) or 'no-profile.png'

        new_user = User(
            username=username,
            email=email,
            phone_number=phone_number,
            role=role,
            name=name,
            profile_image=filename
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash(f"User '{username}' created successfully!", "success")
        return redirect(url_for('admin_user.admin_users'))

    return render_template('admin/user_form.html', edit_mode=False)

@user_bp.route('/users/edit/<username>', methods=['GET', 'POST'], endpoint='edit_user')
@user_bp.route('/user/edit/<username>', methods=['GET', 'POST'], endpoint='admin_edit_user')
@user_bp.route('/users/edit/id/<int:user_id>', methods=['GET', 'POST'], endpoint='edit_user_by_id')
@user_bp.route('/user/edit/<int:user_id>', methods=['GET', 'POST'], endpoint='admin_edit_user_by_id')
@admin_required
def edit_user(username=None, user_id=None):
    user = None
    if user_id:
        user = User.query.get(user_id)
    elif username:
        if str(username).isdigit():
            user = User.query.get(int(username))
        if not user:
            user = User.query.filter_by(username=username).first()

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_user.admin_users'))

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        role = request.form.get('role', 'customer')
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()

        if new_username and new_username != user.username:
            if User.query.filter(User.username == new_username, User.id != user.id).first():
                flash(f"Username '{new_username}' is already taken.", "danger")
                return redirect(url_for('admin_user.admin_edit_user', username=user.username))
            user.username = new_username

        if email and email != user.email:
            if User.query.filter(User.email == email, User.id != user.id).first():
                flash(f"Email '{email}' is already registered.", "danger")
                return redirect(url_for('admin_user.admin_edit_user', username=user.username))
            user.email = email

        if phone_number:
            existing_phone = User.query.filter(User.phone_number == phone_number, User.id != user.id).first()
            if existing_phone:
                flash(f"Phone number '{phone_number}' is already registered to user @{existing_phone.username}.", "danger")
                return redirect(url_for('admin_user.admin_edit_user', username=user.username))
            user.phone_number = phone_number
        elif phone_number == '':
            user.phone_number = ''

        if role:
            user.role = role
        if name:
            user.name = name
        if password:
            user.set_password(password)

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

@user_bp.route('/users/delete/<username>', methods=['POST'], endpoint='delete_user')
@user_bp.route('/user/delete/<username>', methods=['POST'], endpoint='admin_delete_user')
@user_bp.route('/users/delete/id/<int:user_id>', methods=['POST'], endpoint='delete_user_by_id')
@admin_required
def delete_user(username=None, user_id=None):
    user = None
    if user_id:
        user = User.query.get(user_id)
    elif username:
        if str(username).isdigit():
            user = User.query.get(int(username))
        if not user:
            user = User.query.filter_by(username=username).first()

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
