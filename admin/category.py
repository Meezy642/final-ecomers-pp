from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Product
from admin.dashboard import admin_required

category_bp = Blueprint('admin_category', __name__, url_prefix='/admin')

@category_bp.route('/categories')
@admin_required
def admin_categories():
    products = Product.query.all()
    categories = {}
    for p in products:
        cat = p.category or 'uncategorized'
        categories[cat] = categories.get(cat, 0) + 1

    return render_template('admin/categories.html', categories=categories, total_products=len(products))
