import os
import json
from flask import Flask, url_for, session, request, render_template, redirect, flash
from flask_migrate import Migrate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models import db, User, Product, Order, Contact
from upload_config import init_upload_config
from customer import customer_bp
from front import front_bp
from auth import auth_bp
from admin import admin_bp, dashboard_bp, product_bp, category_bp
from items import items

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_heng_key")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize File Upload Configuration
init_upload_config(app)

# Initialize Database & Migrations
db.init_app(app)
migrate = Migrate(app, db)

# Register Blueprints
app.register_blueprint(front_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(product_bp)
app.register_blueprint(category_bp)

# --- SMART URL_FOR RESOLVER FOR COMPATIBILITY ---
ENDPOINT_ALIASES = {
    'admin_dashboard': 'admin_dashboard.admin_dashboard',
    'admin_orders': 'admin_dashboard.admin_orders',
    'admin_contacts': 'admin_dashboard.admin_contacts',
    'user_index': 'admin.user_index',
    'user_create': 'admin.user_create',
    'user_edit': 'admin.user_edit',
    'user_delete': 'admin.user_delete',
    'admin_users': 'admin.user_index',
    'admin_add_user': 'admin.user_create',
    'admin_edit_user': 'admin.user_edit',
    'admin_delete_user': 'admin.user_delete',
    'admin_user.user_index': 'admin.user_index',
    'admin_user.user_create': 'admin.user_create',
    'admin_user.user_edit': 'admin.user_edit',
    'admin_user.user_delete': 'admin.user_delete',
    'admin_user.admin_users': 'admin.user_index',
    'admin_user.add_user': 'admin.user_create',
    'admin_user.edit_user': 'admin.user_edit',
    'admin_user.delete_user': 'admin.user_delete',
    'admin_products': 'admin_product.admin_products',
    'admin_add_product': 'admin_product.admin_add_product',
    'admin_edit_product': 'admin_product.admin_edit_product',
    'admin_delete_product': 'admin_product.admin_delete_product',
    'admin_categories': 'admin_category.admin_categories',
    'home': 'customer.home',
    'products': 'customer.products',
    'contact': 'customer.contact',
    'about': 'customer.about',
    'login': 'customer.login',
    'register': 'customer.register',
    'logout': 'customer.logout',
    'favorites': 'customer.favorites',
    'add_to_wishlist': 'customer.add_to_wishlist',
    'remove_from_wishlist': 'customer.remove_from_wishlist',
    'view_product': 'customer.view_product',
    'add_to_cart': 'customer.add_to_cart',
    'cart': 'customer.cart',
    'increase_cart': 'customer.increase_cart',
    'decrease_cart': 'customer.decrease_cart',
    'remove_from_cart': 'customer.remove_from_cart',
    'clear_cart': 'customer.clear_cart',
    'checkout': 'customer.checkout',
    'place_order': 'customer.place_order',
    'order_success': 'customer.order_success',
    'profile': 'customer.profile',
    'change_profile': 'customer.change_profile',
    'change_password': 'customer.change_password',
    'forgot_password': 'customer.forgot_password',
    'reset_password': 'customer.reset_password',
}

@app.context_processor
def utility_processor():
    orig_url_for = url_for
    def custom_url_for(endpoint, **values):
        # 1. Check alias dictionary first
        target = ENDPOINT_ALIASES.get(endpoint, endpoint)
        if target.startswith('admin_user.'):
            target = target.replace('admin_user.', 'admin.', 1)

        # Attempt direct build
        try:
            return orig_url_for(target, **values)
        except Exception:
            pass

        # Handle id vs user_id parameter name variation
        if 'user_id' in values and 'id' not in values:
            v_id = dict(values)
            v_id['id'] = v_id.pop('user_id')
            try:
                return orig_url_for(target, **v_id)
            except Exception:
                pass
        elif 'id' in values and 'user_id' not in values:
            v_uid = dict(values)
            v_uid['user_id'] = v_uid.pop('id')
            try:
                return orig_url_for(target, **v_uid)
            except Exception:
                pass

        # 2. Try replacing admin_user. with admin.
        if endpoint.startswith('admin_user.'):
            alt_ep = endpoint.replace('admin_user.', 'admin.', 1)
            try:
                return orig_url_for(alt_ep, **values)
            except Exception:
                pass

        # 3. Try blueprint prefixes
        for prefix in ['admin.', 'customer.', 'admin_dashboard.', 'admin_product.', 'admin_category.']:
            try:
                return orig_url_for(prefix + endpoint, **values)
            except Exception:
                pass

        return orig_url_for(endpoint, **values)
    return dict(url_for=custom_url_for)

# --- GLOBAL CONTEXT PROCESSOR FOR CART & USER INFO ---
@app.context_processor
def inject_global_template_vars():
    # 1. Cart Count
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}
    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0

    # 2. Wishlist Count
    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []
    wishlist_count = len(wishlist) if isinstance(wishlist, list) else 0

    # 3. Logged-in User, Role, Profile Pic & Display Name
    logged_in_user = session.get('username')
    logged_in_user_role = None
    logged_in_user_pic = None
    logged_in_user_display_name = None
    if logged_in_user:
        try:
            user = User.query.filter_by(username=logged_in_user).first()
            if user:
                logged_in_user_role = user.role
                pic = user.profile_image if user.profile_image and user.profile_image != 'no-profile.png' else ''
                if pic and not pic.startswith('/') and not pic.startswith('http') and not pic.startswith('data:'):
                    pic = f"/static/uploads/{pic}"
                logged_in_user_pic = pic
                logged_in_user_display_name = user.name or user.username
        except Exception:
            pass

    return dict(
        cart_count=cart_count,
        wishlist_count=wishlist_count,
        wishlist=wishlist,
        logged_in_user=logged_in_user,
        logged_in_user_role=logged_in_user_role,
        logged_in_user_pic=logged_in_user_pic,
        logged_in_user_display_name=logged_in_user_display_name
    )

# --- DATABASE SEEDING & INITIALIZATION ---
with app.app_context():
    db.create_all()

    # 1. Seed Products from items.py if empty
    if Product.query.count() == 0:
        for itm in items:
            rating = itm.get('rating', {})
            p = Product(
                id=itm['id'],
                title=itm['title'],
                price=float(itm['price']),
                description=itm.get('description', ''),
                category=itm.get('category', 'general'),
                image=itm.get('image', ''),
                rating_rate=float(rating.get('rate', 4.0)),
                rating_count=int(rating.get('count', 0))
            )
            db.session.add(p)
        db.session.commit()
        print("Seeded products successfully into SQLite database.")

    # 2. Seed Users from users.json if empty, or ensure default admin
    if User.query.count() == 0:
        if os.path.exists('users.json'):
            try:
                with open('users.json', 'r') as f:
                    u_data = json.load(f)
                    for u_name, u_info in u_data.items():
                        new_u = User(
                            username=u_name,
                            email=u_info.get('email', f"{u_name}@localhost.com"),
                            role=u_info.get('role', 'customer'),
                            name=u_info.get('name', u_name),
                            profile_image=u_info.get('profile_pic') or 'no-profile.png'
                        )
                        new_u.set_password(u_info.get('password', '123456'))
                        db.session.add(new_u)
                    db.session.commit()
            except Exception as e:
                print(f"Error seeding users from users.json: {e}")

    # Ensure admin user exists
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@localhost.com',
            role='admin',
            name='Administrator',
            profile_image='no-profile.png'
        )
        admin_user.set_password('admin')
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created (admin / admin).")

    # 3. Seed Orders from orders.json if empty
    if Order.query.count() == 0 and os.path.exists('orders.json'):
        try:
            with open('orders.json', 'r') as f:
                orders_data = json.load(f)
                for user_key, order_list in orders_data.items():
                    for ord_item in order_list:
                        new_o = Order(
                            order_id=ord_item.get('order_id', f"YS-{ord_item.get('timestamp', '')[:6]}"),
                            username=user_key if user_key != 'guest' else None,
                            buyer_name=ord_item.get('buyer_name', ''),
                            buyer_phone=ord_item.get('buyer_phone', ''),
                            buyer_email=ord_item.get('buyer_email', ''),
                            buyer_address=ord_item.get('buyer_address', ''),
                            order_notes=ord_item.get('order_notes', ''),
                            payment_method=ord_item.get('payment_method', 'Bakong KHQR - Paid'),
                            total_price=float(ord_item.get('total_price', 0.0)),
                            items_json=json.dumps(ord_item.get('items', [])),
                            timestamp=ord_item.get('timestamp', '')
                        )
                        db.session.add(new_o)
                db.session.commit()
        except Exception as e:
            print(f"Error seeding orders: {e}")

    # 4. Seed Contacts from contacts.json if empty
    if Contact.query.count() == 0 and os.path.exists('contacts.json'):
        try:
            with open('contacts.json', 'r') as f:
                contacts_data = json.load(f)
                for c_item in contacts_data:
                    new_c = Contact(
                        name=c_item.get('name', 'Anonymous'),
                        email=c_item.get('email', 'no-reply@example.com'),
                        subject=c_item.get('subject', ''),
                        message=c_item.get('message', '')
                    )
                    db.session.add(new_c)
                db.session.commit()
        except Exception as e:
            print(f"Error seeding contacts: {e}")

# --- ADMIN PORTAL AUTHENTICATION ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('username') and session.get('user_role') in ['admin', 'Super Administrator']:
        return redirect(request.args.get('next') or url_for('admin_dashboard.admin_dashboard'))

    if request.method == 'POST':
        identity = request.form.get('identity') or request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # 1. Check database user
        user = User.query.filter((User.username == identity) | (User.email == identity)).first()

        if user and user.check_password(password) and user.role == 'admin':
            session.clear()
            session.permanent = bool(request.form.get('remember_me') or request.form.get('remember'))
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_email'] = user.email
            session['user_role'] = 'admin'
            flash(f"Welcome back, {user.name or user.role}!", "success")
            return redirect(request.args.get('next') or url_for('admin_dashboard.admin_dashboard'))

        # 2. Check superadmin fallback credentials
        elif identity in ['admin@store.com', 'admin@pspstore.com', 'kry lyheng', 'admin'] and password in ['admin123', 'admin']:
            session.clear()
            session.permanent = bool(request.form.get('remember_me') or request.form.get('remember'))
            session['user_id'] = 9999
            session['username'] = 'Kry Lyheng'
            session['user_email'] = 'admin@store.com'
            session['user_role'] = 'Super Administrator'
            flash("Welcome back, Super Administrator!", "success")
            return redirect(request.args.get('next') or url_for('admin_dashboard.admin_dashboard'))

        elif user and user.role != 'admin':
            flash("Access denied. Administrator or Staff privileges required for this portal.", "danger")
        else:
            flash("Invalid username or password.", "danger")

    return render_template('admin/auth/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash("You have been logged out of the admin portal.", "success")
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)