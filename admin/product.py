import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, Product
from upload_config import save_uploaded_file
from admin.dashboard import admin_required

product_bp = Blueprint('admin_product', __name__, url_prefix='/admin')

@product_bp.route('/products')
@admin_required
def admin_products():
    products = [p.to_dict() for p in Product.query.order_by(Product.id.asc()).all()]
    return render_template('admin/products.html', products=products)

@product_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    categories = [c[0] for c in db.session.query(Product.category).distinct().all() if c[0]]

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        price = float(request.form.get('price', 0) or 0)
        category = request.form.get('category', '').strip()
        new_category = request.form.get('new_category', '').strip()
        description = request.form.get('description', '').strip()
        image_url = request.form.get('image', '').strip()
        rating_rate = float(request.form.get('rating_rate', 4.0) or 4.0)
        rating_count = int(request.form.get('rating_count', 0) or 0)

        if category == '__new__' and new_category:
            category = new_category

        # Check for file upload
        uploaded_file = request.files.get('image_file') or request.files.get('image')
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        filename = save_uploaded_file(uploaded_file, upload_folder=upload_folder)
        
        final_image = f"/static/admin/uploads/{filename}" if filename else image_url

        new_product = Product(
            title=title,
            price=price,
            description=description,
            category=category,
            image=final_image,
            rating_rate=rating_rate,
            rating_count=rating_count
        )
        db.session.add(new_product)
        db.session.commit()
        flash(f"Product '{title}' added successfully!", "success")
        return redirect(url_for('admin_product.admin_products'))

    return render_template('admin/product_form.html',
        edit_mode=False,
        categories=categories
    )

@product_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('admin_product.admin_products'))

    categories = [c[0] for c in db.session.query(Product.category).distinct().all() if c[0]]

    if request.method == 'POST':
        product.title = request.form.get('title', '').strip()
        product.price = float(request.form.get('price', 0) or 0)
        category = request.form.get('category', '').strip()
        new_category = request.form.get('new_category', '').strip()
        if category == '__new__' and new_category:
            category = new_category
        product.category = category
        product.description = request.form.get('description', '').strip()
        
        image_url = request.form.get('image', '').strip()
        uploaded_file = request.files.get('image_file') or request.files.get('image')
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        filename = save_uploaded_file(uploaded_file, upload_folder=upload_folder)
        if filename:
            product.image = f"/static/admin/uploads/{filename}"
        elif image_url:
            product.image = image_url

        product.rating_rate = float(request.form.get('rating_rate', 4.0) or 4.0)
        product.rating_count = int(request.form.get('rating_count', 0) or 0)

        db.session.commit()
        flash(f"Product '{product.title}' updated successfully!", "success")
        return redirect(url_for('admin_product.admin_products'))

    return render_template('admin/product_form.html',
        edit_mode=True,
        product=product.to_dict(),
        categories=categories
    )

@product_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('admin_product.admin_products'))

    title = product.title
    db.session.delete(product)
    db.session.commit()
    flash(f"Product '{title}' deleted successfully!", "success")
    return redirect(url_for('admin_product.admin_products'))
