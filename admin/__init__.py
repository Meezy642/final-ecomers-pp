from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

from admin import user
from admin.dashboard import dashboard_bp
from admin.product import product_bp
from admin.category import category_bp
