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
        if cat not in categories:
            categories[cat] = {
                'name': cat,
                'count': 0,
                'total_value': 0.0,
                'sample_image': p.image
            }
        categories[cat]['count'] += 1
        categories[cat]['total_value'] += p.price or 0.0

    category_list = sorted(list(categories.values()), key=lambda x: x['count'], reverse=True)
    return render_template('admin/categories.html', categories=category_list)
