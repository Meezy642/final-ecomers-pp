from flask import Blueprint, redirect, url_for

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def admin_root():
    return redirect(url_for('admin.user_index'))

from admin import user
from admin.dashboard import dashboard_bp
from admin.product import product_bp
from admin.category import category_bp
