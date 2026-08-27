import os
import json
import random
import datetime
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, render_template, request, redirect, url_for, make_response, session, flash, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer
from models import db, User, Product, Order, Contact
from upload_config import save_uploaded_file

customer_bp = Blueprint('customer', __name__)

# --- TELEGRAM BOT CONFIGURATION ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8797666810:AAFNxpfrEAzVrUVTSYc8cGOwChHRc56AesU")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1003719714118,1415187900")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# --- SMTP EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "ystaashopp@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "vivsqpkvpsweihtd")

def send_reset_email(to_email, username, reset_url):
    if not SMTP_PASSWORD:
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"YSTAA SHOPP <{SMTP_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = "Reset Your Password"
        
        text_body = (
            f"Hello {username},\n\n"
            f"We received a request to reset your password for your YSTAA SHOPP account. "
            f"Click the link below to choose a new password. This link is valid for 1 hour:\n\n"
            f"{reset_url}\n\n"
            f"If you did not request a password reset, you can safely ignore this email.\n\n"
            f"YSTAA SHOPP - Phnom Penh, Cambodia"
        )
        
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reset Your Password - YSTAA SHOPP</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #0b0f19; color: #e2e8f0; padding: 20px;">
    <div style="max-width: 600px; margin: auto; background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 30px;">
        <h1 style="color: #7c3aed; text-align: center;">YSTAA SHOPP</h1>
        <h2>Hello {username},</h2>
        <p>We received a request to reset your password. Click the button below to choose a new password:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background: #7c3aed; color: #fff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: bold;">Reset Password</a>
        </div>
        <p style="font-size: 12px; color: #64748b;">If you did not request a password reset, you can safely ignore this email.</p>
    </div>
</body>
</html>"""
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send reset email: {e}")
        return False

def send_telegram_message(text):
    chat_ids = [cid.strip() for cid in CHAT_ID.split(",") if cid.strip()]
    headers = {"accept": "application/json", "content-type": "application/json"}
    for cid in chat_ids:
        payload = {"text": text, "parse_mode": "HTML", "chat_id": cid}
        try:
            requests.post(TELEGRAM_URL, json=payload, headers=headers, timeout=5)
        except Exception as e:
            print(f"Telegram notification error: {e}")

@customer_bp.route('/')
def home():
    items = [p.to_dict() for p in Product.query.order_by(Product.id.asc()).all()]
    return render_template('customer/index.html', item=items)

@customer_bp.route('/product')
def products():
    q = request.args.get('q', '').strip()
    selected_categories = request.args.getlist('category')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort', '')

    query = Product.query
    if q:
        query = query.filter((Product.title.ilike(f'%{q}%')) | (Product.description.ilike(f'%{q}%')))
    if selected_categories:
        query = query.filter(Product.category.in_(selected_categories))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if sort_by == 'low_high':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'high_low':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'rating':
        query = query.order_by(Product.rating_rate.desc())
    else:
        query = query.order_by(Product.id.asc())

    filtered_items = [p.to_dict() for p in query.all()]

    return render_template(
        'customer/products.html',
        item=filtered_items,
        current_q=q,
        current_categories=selected_categories,
        current_min_price=min_price,
        current_max_price=max_price,
        current_sort=sort_by
    )

@customer_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        new_contact = Contact(name=name, email=email, subject=subject, message=message)
        db.session.add(new_contact)
        db.session.commit()

        telegram_text = (
            f"<b>✉️ NEW CONTACT INQUIRY RECEIVED</b>\n"
            f"<b>----------------------------------</b>\n\n"
            f"👤 <b>Name:</b> {name}\n"
            f"📧 <b>Email:</b> <code>{email}</code>\n"
            f"📝 <b>Subject:</b> {subject}\n\n"
            f"💬 <b>Message:</b>\n<i>{message}</i>"
        )
        send_telegram_message(telegram_text)

        flash("Thank you! Your message has been sent successfully.", "success")
        return redirect(url_for('customer.contact'))

    return render_template('customer/contact.html')

@customer_bp.route('/api/book_showroom', methods=['POST'])
def book_showroom():
    data = request.get_json() or {}
    name = data.get('name')
    phone = data.get('phone')
    service = data.get('service')
    advisor = data.get('advisor')
    date_val = data.get('date')
    time_slot = data.get('time')
    notes = data.get('notes', '')

    telegram_text = (
        f"<b>👑 NEW VIP SHOWROOM BOOKING</b>\n"
        f"<b>----------------------------------</b>\n\n"
        f"👤 <b>Client:</b> {name}\n"
        f"📞 <b>Phone:</b> <code>{phone}</code>\n"
        f"📅 <b>Date:</b> {date_val}\n"
        f"⏰ <b>Time:</b> {time_slot}\n"
        f"💎 <b>Service:</b> {service}\n"
        f"👔 <b>Advisor:</b> {advisor}\n"
    )
    if notes:
        telegram_text += f"\n📝 <b>Special Requests:</b>\n<i>{notes}</i>"

    send_telegram_message(telegram_text)
    return jsonify({"success": True})

@customer_bp.route('/about')
def about():
    return render_template('customer/about.html')

# --- AUTHENTICATION ---

@customer_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect them directly
    if 'username' in session:
        logged_in_user = User.query.filter_by(username=session['username']).first()
        if logged_in_user and logged_in_user.role in ['admin', 'staff']:
            return redirect(url_for('admin_dashboard.admin_dashboard'))
        elif session.get('user_role') in ['admin', 'staff', 'Super Administrator']:
            return redirect(url_for('admin_dashboard.admin_dashboard'))
        return redirect(url_for('customer.home'))

    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()

        if user and user.check_password(password):
            session['username'] = user.username
            session['user_role'] = user.role
            flash(f"Welcome back, {user.name or user.username}!", "success")
            
            if user.role in ['admin', 'staff']:
                return redirect(url_for('admin_dashboard.admin_dashboard'))
            return redirect(url_for('customer.home'))
        else:
            flash("Invalid username/email or password.", "error")
            return redirect(url_for('customer.login'))

    return render_template('share/login.html')

@customer_bp.route('/register', methods=['GET', 'POST'])
def register():
    # If user is already logged in, redirect them directly
    if 'username' in session:
        logged_in_user = User.query.filter_by(username=session['username']).first()
        if logged_in_user and logged_in_user.role in ['admin', 'staff']:
            return redirect(url_for('admin_dashboard.admin_dashboard'))
        elif session.get('user_role') in ['admin', 'staff', 'Super Administrator']:
            return redirect(url_for('admin_dashboard.admin_dashboard'))
        return redirect(url_for('customer.home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for('customer.register'))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('customer.register'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return redirect(url_for('customer.register'))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for('customer.register'))

        new_user = User(username=username, email=email, role='customer', name=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        session['username'] = username
        flash("Account created successfully! Welcome to the shop.", "success")
        return redirect(url_for('customer.home'))

    return render_template('share/register.html')

@customer_bp.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have logged out successfully.", "success")
    return redirect(url_for('customer.home'))

# --- WISHLIST ---

@customer_bp.route('/favorites')
def favorites():
    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []

    products = Product.query.filter(Product.id.in_(wishlist)).all() if wishlist else []
    wishlist_items = [p.to_dict() for p in products]
    return render_template('customer/wishlist.html', wishlist_items=wishlist_items)

@customer_bp.route('/add_to_wishlist/<int:item_id>', methods=['POST'])
def add_to_wishlist(item_id):
    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []

    if item_id not in wishlist:
        wishlist.append(item_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = make_response(jsonify({'success': True, 'wishlist_count': len(wishlist)}))
        response.headers['Content-Type'] = 'application/json'
        response.set_cookie('wishlist', json.dumps(wishlist), max_age=60 * 60 * 24 * 7)
        return response

    response = make_response(redirect(request.referrer or url_for('customer.products')))
    response.set_cookie('wishlist', json.dumps(wishlist), max_age=60 * 60 * 24 * 7)
    return response

@customer_bp.route('/remove_from_wishlist/<int:item_id>', methods=['POST'])
def remove_from_wishlist(item_id):
    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []

    if item_id in wishlist:
        wishlist.remove(item_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = make_response(jsonify({'success': True, 'wishlist_count': len(wishlist)}))
        response.headers['Content-Type'] = 'application/json'
        response.set_cookie('wishlist', json.dumps(wishlist), max_age=60 * 60 * 24 * 7)
        return response

    response = make_response(redirect(request.referrer or url_for('customer.favorites')))
    response.set_cookie('wishlist', json.dumps(wishlist), max_age=60 * 60 * 24 * 7)
    return response

# --- CART ---

@customer_bp.route('/view_product/<int:item_id>')
def view_product(item_id):
    product = Product.query.get(item_id)
    if not product:
        return render_template('customer/404.html'), 404

    current_item = product.to_dict()
    related = Product.query.filter(Product.category == product.category, Product.id != item_id).limit(4).all()
    related_products = [p.to_dict() for p in related]

    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []
    in_wishlist = item_id in wishlist

    return render_template(
        'customer/view_product.html',
        item=current_item,
        related_products=related_products,
        in_wishlist=in_wishlist
    )

@customer_bp.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    cart[str_item_id] = cart.get(str_item_id, 0) + 1

    product = Product.query.get(item_id)
    prod_title = product.title[:20] + "..." if product else "Product"
    cart_count = sum(cart.values())

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = make_response(jsonify({
            "success": True,
            "cart_count": cart_count,
            "message": f"Added {prod_title} to your cart!"
        }))
        response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
        return response

    flash(f"Added {prod_title} to your cart!", "success")
    response = make_response(redirect(request.referrer or url_for('customer.cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

@customer_bp.route('/cart')
def cart():
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    cart_items = []
    total_price = 0

    if cart:
        product_ids = [int(k) for k in cart.keys() if str(k).isdigit()]
        products = {p.id: p.to_dict() for p in Product.query.filter(Product.id.in_(product_ids)).all()}
        
        for item_id_str, quantity in cart.items():
            try:
                pid = int(item_id_str)
                product = products.get(pid)
                if product:
                    item_total = product['price'] * quantity
                    total_price += item_total
                    cart_items.append({
                        'product': product,
                        'quantity': quantity,
                        'item_total': round(item_total, 2)
                    })
            except Exception:
                continue

    return render_template(
        'customer/cart.html',
        cart_items=cart_items,
        total_price=round(total_price, 2)
    )

@customer_bp.route('/increase_cart/<int:item_id>', methods=['POST'])
def increase_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart[str_item_id] += 1

    response = make_response(redirect(url_for('customer.cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

@customer_bp.route('/decrease_cart/<int:item_id>', methods=['POST'])
def decrease_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        if cart[str_item_id] > 1:
            cart[str_item_id] -= 1
        else:
            cart.pop(str_item_id)

    response = make_response(redirect(url_for('customer.cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

@customer_bp.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart.pop(str_item_id)

    flash("Item removed from cart.", "success")
    response = make_response(redirect(url_for('customer.cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

@customer_bp.route('/clear_cart')
def clear_cart():
    flash("Shopping cart cleared.", "success")
    response = make_response(redirect(url_for('customer.cart')))
    response.delete_cookie('cart')
    return response

# --- CHECKOUT & ORDERS ---

@customer_bp.route('/checkout')
def checkout():
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    cart_items = []
    total_price = 0

    if cart:
        product_ids = [int(k) for k in cart.keys() if str(k).isdigit()]
        products = {p.id: p.to_dict() for p in Product.query.filter(Product.id.in_(product_ids)).all()}
        
        for item_id_str, quantity in cart.items():
            try:
                pid = int(item_id_str)
                product = products.get(pid)
                if product:
                    item_total = product['price'] * quantity
                    total_price += item_total
                    cart_items.append({
                        'product': product,
                        'quantity': quantity,
                        'item_total': round(item_total, 2)
                    })
            except Exception:
                continue

    if not cart_items:
        flash("Your cart is empty. Please add items before checkout.", "error")
        return redirect(url_for('customer.cart'))

    user_email = ""
    username = session.get('username')
    if username:
        user = User.query.filter_by(username=username).first()
        user_email = user.email if user else ""

    return render_template(
        'customer/checkout.html',
        cart_items=cart_items,
        total_price=round(total_price, 2),
        buyer_username=username,
        buyer_email=user_email
    )

@customer_bp.route('/place_order', methods=['POST'])
def place_order():
    buyer_name = request.form.get('buyer_name', '').strip()
    buyer_phone = request.form.get('buyer_phone', '').strip()
    buyer_email = request.form.get('buyer_email', '').strip()
    buyer_address = request.form.get('buyer_address', '').strip()
    order_notes = request.form.get('order_notes', 'N/A').strip()
    
    payment_method = request.form.get('payment_method', 'khqr')
    if payment_method == 'card':
        payment_display = "Visa / MasterCard - Paid"
    elif payment_method == 'paypal':
        payment_display = "PayPal Account - Paid"
    else:
        payment_display = "Bakong KHQR - Paid"

    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    if not cart:
        flash("Your cart was empty. Order failed.", "error")
        return redirect(url_for('customer.cart'))

    product_ids = [int(k) for k in cart.keys() if str(k).isdigit()]
    products = {p.id: p.to_dict() for p in Product.query.filter(Product.id.in_(product_ids)).all()}

    items_list = []
    item_list_text = ""
    total_price = 0

    for item_id_str, quantity in cart.items():
        try:
            pid = int(item_id_str)
            product = products.get(pid)
            if product:
                item_total = product['price'] * quantity
                total_price += item_total
                items_list.append({
                    "title": product['title'],
                    "quantity": quantity,
                    "price": product['price'],
                    "image": product['image']
                })
                item_list_text += f"📦 <b>{product['title'][:25]}...</b>\n"
                item_list_text += f"   └ Qty: {quantity} × ${product['price']:.2f} = <b>${item_total:.2f}</b>\n\n"
        except Exception:
            continue

    order_id = f"YS-{random.randint(100000, 999999)}"
    timestamp = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    username = session.get('username')

    new_order = Order(
        order_id=order_id,
        username=username,
        buyer_name=buyer_name,
        buyer_phone=buyer_phone,
        buyer_email=buyer_email,
        buyer_address=buyer_address,
        order_notes=order_notes,
        payment_method=payment_display,
        total_price=round(total_price, 2),
        items_json=json.dumps(items_list),
        timestamp=timestamp
    )
    db.session.add(new_order)
    db.session.commit()

    session['last_order'] = new_order.to_dict()

    telegram_text = (
        f"<b>🔔 NEW ORDER RECEIVED ({payment_method.upper()})</b>\n"
        f"<b>----------------------------------</b>\n\n"
        f"👤 <b>Customer:</b> {buyer_name}\n"
        f"📞 <b>Phone:</b> <code>{buyer_phone}</code>\n"
        f"📧 <b>Email:</b> <code>{buyer_email}</code>\n"
        f"📍 <b>Address:</b> {buyer_address}\n"
        f"📝 <b>Notes:</b> <i>{order_notes}</i>\n\n"
        f"<b>🛒 ORDER ITEMS:</b>\n{item_list_text}"
        f"<b>----------------------------------</b>\n"
        f"💰 <b>TOTAL PAID: ${total_price:.2f} USD ({payment_display})</b>"
    )
    send_telegram_message(telegram_text)

    response = make_response(redirect(url_for('customer.order_success')))
    response.delete_cookie('cart')
    return response

@customer_bp.route('/order_success')
def order_success():
    order = session.get('last_order')
    if not order:
        return redirect(url_for('customer.home'))
    return render_template('customer/order_success.html', order=order)

# --- PROFILE & SETTINGS ---

@customer_bp.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        flash("Please log in to view your profile.", "error")
        return redirect(url_for('customer.login'))
        
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('customer.login'))
        
    email = user.email or 'N/A'
    profile_pic = user.profile_image if user.profile_image and user.profile_image != 'no-profile.png' else ''
    if profile_pic and not profile_pic.startswith('/') and not profile_pic.startswith('http') and not profile_pic.startswith('data:'):
        profile_pic = f"/static/uploads/{profile_pic}"
        
    role = user.role or 'customer'
    name = user.name or username
    
    layout_template = 'admin/layout.html' if role == 'admin' else 'customer/layout.html'
    
    orders = [o.to_dict() for o in Order.query.filter_by(username=username).order_by(Order.id.desc()).all()]
    
    return render_template(
        'customer/profile.html', 
        username=username, 
        email=email, 
        name=name,
        orders=orders,
        profile_pic=profile_pic,
        layout_template=layout_template
    )

@customer_bp.route('/change_profile', methods=['POST'])
def change_profile():
    if 'username' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('customer.login'))
        
    username = session['username']
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone_number = request.form.get('phone_number', '').strip()
    
    if not email:
        flash("Email is required.", "error")
        return redirect(url_for('customer.profile'))
        
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('customer.profile'))

    # Check for duplicate email across other accounts
    if email != user.email:
        if User.query.filter(User.email == email, User.id != user.id).first():
            flash(f"Email '{email}' is already registered to another account.", "error")
            return redirect(url_for('customer.profile'))
        user.email = email

    # Check for duplicate phone across other accounts
    if phone_number and phone_number != user.phone_number:
        if User.query.filter(User.phone_number == phone_number, User.id != user.id).first():
            flash(f"Phone number '{phone_number}' is already registered to another account.", "error")
            return redirect(url_for('customer.profile'))
        user.phone_number = phone_number

    if name:
        user.name = name

    db.session.commit()
    flash("Profile updated successfully.", "success")
    return redirect(url_for('customer.profile'))

@customer_bp.route('/api/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'username' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({"success": False, "message": "No image data received"}), 400
        
    username = session['username']
    user = User.query.filter_by(username=username).first()
    if user:
        user.profile_image = image_data
        db.session.commit()
        return jsonify({"success": True, "message": "Profile picture updated successfully!"})
        
    return jsonify({"success": False, "message": "User not found"}), 404

@customer_bp.route('/api/delete_avatar', methods=['POST'])
def delete_avatar():
    if 'username' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    username = session['username']
    user = User.query.filter_by(username=username).first()
    if user:
        user.profile_image = 'no-profile.png'
        db.session.commit()
        return jsonify({"success": True, "message": "Profile picture removed successfully!"})
        
    return jsonify({"success": False, "message": "User not found"}), 404

@customer_bp.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('customer.login'))
        
    username = session['username']
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_password or not new_password or not confirm_password:
        flash("All password fields are required.", "error")
        return redirect(url_for('customer.profile'))
        
    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for('customer.profile'))
        
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(current_password):
        flash("Incorrect current password.", "error")
        return redirect(url_for('customer.profile'))
        
    user.set_password(new_password)
    db.session.commit()
    
    flash("Your password has been updated successfully.", "success")
    return redirect(url_for('customer.profile'))

@customer_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash("Please enter your email address.", "error")
            return redirect(url_for('customer.forgot_password'))
            
        user = User.query.filter_by(email=email).first()
        if user:
            serializer = URLSafeTimedSerializer(current_app.secret_key)
            token = serializer.dumps(user.username, salt='password-reset-salt')
            
            host = request.headers.get('X-Forwarded-Host') or request.headers.get('Host') or request.host
            proto = request.headers.get('X-Forwarded-Proto') or request.scheme
            base_url = f"{proto}://{host}"
            reset_url = base_url.rstrip('/') + url_for('customer.reset_password', token=token)

            send_reset_email(email, user.username, reset_url)
            print(f"Password reset link generated for {user.username}: {reset_url}", flush=True)

        flash("If your email is registered, we have sent a reset link to it. Please check your inbox.", "success")
        return redirect(url_for('customer.login'))
        
    return render_template('share/forgot_password.html')

@customer_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        username = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception:
        username = None
        
    if not username:
        flash("The reset link is invalid or has expired.", "error")
        return redirect(url_for('customer.login'))
        
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or not confirm_password:
            flash("Please enter and confirm your new password.", "error")
            return render_template('share/reset_password.html')
            
        if new_password != confirm_password:
            flash("New passwords do not match.", "error")
            return render_template('share/reset_password.html')
            
        user = User.query.filter_by(username=username).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            flash("Your password has been reset successfully. Please log in with your new password.", "success")
            return redirect(url_for('customer.login'))
        else:
            flash("User not found.", "error")
            return redirect(url_for('customer.login'))
            
    return render_template('share/reset_password.html')

@customer_bp.route('/api/track_order/<order_id>')
def track_order_api(order_id):
    order = Order.query.filter(db.func.upper(Order.order_id) == str(order_id).strip().upper()).first()
    if order:
        return jsonify({
            "success": True,
            "order_id": order.order_id,
            "buyer_name": order.buyer_name,
            "timestamp": order.timestamp,
            "total_price": order.total_price,
            "items": json.loads(order.items_json) if order.items_json else [],
            "status_text": "Dispatched & In Transit",
            "status_code": 3
        })
    return jsonify({
        "success": False,
        "message": f"Order ID '{order_id}' not found. Please verify the code and try again."
    })
