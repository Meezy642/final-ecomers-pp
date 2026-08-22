from flask import Blueprint, render_template, session, redirect, url_for, flash
from functools import wraps
from models import db, User, Product, Order, Contact

dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = session.get('username')
        if not username:
            flash("Please log in to access the admin panel.", "error")
            return redirect(url_for('customer.login'))
        user = User.query.filter_by(username=username).first()
        if not user or user.role != 'admin':
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for('customer.home'))
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    users = User.query.all()
    products = Product.query.all()
    orders = Order.query.all()
    
    total_revenue = sum((o.total_price or 0) for o in orders)
    
    categories = {}
    for p in products:
        cat = p.category or 'uncategorized'
        categories[cat] = categories.get(cat, 0) + 1
        
    recent_orders = [o.to_dict() for o in Order.query.order_by(Order.id.desc()).limit(5).all()]

    return render_template('admin/dashboard.html',
        total_users=len(users),
        total_products=len(products),
        total_orders=len(orders),
        total_revenue=round(total_revenue, 2),
        categories=categories,
        recent_orders=recent_orders,
        users={u.username: u.to_dict() for u in users}
    )

@dashboard_bp.route('/orders')
@admin_required
def admin_orders():
    orders = [o.to_dict() for o in Order.query.order_by(Order.id.desc()).all()]
    return render_template('admin/orders.html', orders=orders)

@dashboard_bp.route('/contacts')
@admin_required
def admin_contacts():
    contacts = [c.to_dict() for c in Contact.query.order_by(Contact.id.desc()).all()]
    return render_template('admin/contacts.html', contacts=contacts)
