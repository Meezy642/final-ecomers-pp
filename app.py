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
from admin import dashboard_bp, product_bp, category_bp, user_bp
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
app.register_blueprint(customer_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(product_bp)
app.register_blueprint(category_bp)
app.register_blueprint(user_bp)

# --- SMART URL_FOR RESOLVER FOR COMPATIBILITY ---
@app.context_processor
def utility_processor():
    orig_url_for = url_for
    def custom_url_for(endpoint, **values):
        try:
            return orig_url_for(endpoint, **values)
        except Exception:
            # Fallbacks for blueprint prefixes
            for prefix in ['customer.', 'admin_dashboard.', 'admin_user.', 'admin_product.', 'admin_category.']:
                try:
                    return orig_url_for(prefix + endpoint, **values)
                except Exception:
                    pass
            if '.' in endpoint:
                base = endpoint.split('.', 1)[1]
                try:
                    return orig_url_for(base, **values)
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
                    pic = f"/static/admin/uploads/{pic}"
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
                            password=u_info.get('password', '123456'),
                            role=u_info.get('role', 'customer'),
                            name=u_info.get('name', u_name),
                            profile_image=u_info.get('profile_pic') or 'no-profile.png'
                        )
                        db.session.add(new_u)
                    db.session.commit()
            except Exception as e:
                print(f"Error seeding users from users.json: {e}")

    # Ensure admin user exists
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@localhost.com',
            password='admin',
            role='admin',
            name='Administrator',
            profile_image='no-profile.png'
        )
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)