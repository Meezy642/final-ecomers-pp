from flask import Blueprint, redirect, url_for, session, request, flash
from models.user import User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def require_admin_login():
    if request.endpoint in ['admin_login', 'admin_logout', 'static']:
        return None
    if not session.get('username'):
        flash("Session expired or removed. Please log in to access the admin portal.", "danger")
        return redirect(url_for('admin_login'))

@admin_bp.route('/')
def admin_root():
    return redirect(url_for('admin.user_index'))

from admin import user
from admin.dashboard import dashboard_bp
from admin.product import product_bp
from admin.category import category_bp
