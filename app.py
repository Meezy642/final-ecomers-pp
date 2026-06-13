import os
import json
import requests
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, make_response, session, flash, jsonify
from dotenv import load_dotenv
from items import items

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "premium_ecommerce_secret_key_1337_ystaa")

# --- TELEGRAM BOT CONFIGURATION ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8797666810:AAFNxpfrEAzVrUVTSYc8cGOwChHRc56AesU")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1003719714118,1415187900")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

RESET_TOKENS = {}

# --- SMTP EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "ystaashopp@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "vivsqpkvpsweihtd")

def send_reset_email(to_email, username, reset_url):
    if not SMTP_PASSWORD:
        print("SMTP_PASSWORD is not configured. Skipping email dispatch.", flush=True)
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"YSTAA SHOPP <{SMTP_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = "Reset Your Password"
        
        body = f"Hello {username},\n\nReset your password:\n\n{reset_url}"
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        print(f"Password reset email sent to {to_email} successfully.", flush=True)
        return True
    except Exception as e:
        print(f"Failed to send reset email to {to_email}: {e}", flush=True)
        return False


def send_telegram_message(text):
    chat_ids = [cid.strip() for cid in CHAT_ID.split(",") if cid.strip()]
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    for cid in chat_ids:
        payload = {
            "text": text,
            "parse_mode": "HTML",
            "chat_id": cid
        }
        try:
            telegram_response = requests.post(TELEGRAM_URL, json=payload, headers=headers, timeout=5)
            print(f"Telegram Bot Status for {cid}: {telegram_response.status_code}", flush=True)
        except Exception as e:
            print(f"Failed to push notification to Telegram for {cid}: {e}", flush=True)

# File database mock helpers (Vercel has a read-only filesystem, so use /tmp)
IS_VERCEL = os.environ.get("VERCEL") or os.environ.get("NOW_REGION")

if IS_VERCEL:
    USERS_FILE = '/tmp/users.json'
    CONTACTS_FILE = '/tmp/contacts.json'
    ORDERS_FILE = '/tmp/orders.json'
    
    # Copy initial files if they exist in the project root but not in /tmp
    import shutil
    for f_name in ['users.json', 'orders.json']:
        tmp_path = f'/tmp/{f_name}'
        if not os.path.exists(tmp_path) and os.path.exists(f_name):
            try:
                shutil.copy(f_name, tmp_path)
            except Exception as e:
                print(f"Error copying initial DB file {f_name}: {e}")
else:
    USERS_FILE = 'users.json'
    CONTACTS_FILE = 'contacts.json'
    ORDERS_FILE = 'orders.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        print(f"Error saving users: {e}")

def save_contact(contact_data):
    contacts = []
    if os.path.exists(CONTACTS_FILE):
        try:
            with open(CONTACTS_FILE, 'r') as f:
                contacts = json.load(f)
        except Exception:
            contacts = []
    contacts.append(contact_data)
    try:
        with open(CONTACTS_FILE, 'w') as f:
            json.dump(contacts, f, indent=4)
    except Exception as e:
        print(f"Error saving contact query: {e}")


def save_order(username, order_data):
    orders = {}
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r') as f:
                orders = json.load(f)
        except Exception:
            orders = {}
            
    key = username if username else "guest"
    if key not in orders:
        orders[key] = []
        
    orders[key].append(order_data)
    try:
        with open(ORDERS_FILE, 'w') as f:
            json.dump(orders, f, indent=4)
    except Exception as e:
        print(f"Error saving order: {e}")

def load_orders(username):
    if not os.path.exists(ORDERS_FILE):
        return []
    try:
        with open(ORDERS_FILE, 'r') as f:
            orders = json.load(f)
            return orders.get(username, [])
    except Exception:
        return []

# --- GLOBAL CONTEXT PROCESSOR ---
@app.context_processor
def inject_global_template_vars():
    # 1. Cart Count
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}
    cart_count = sum(cart.values())

    # 2. Wishlist Count
    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []
    wishlist_count = len(wishlist)

    # 3. Logged-in User
    logged_in_user = session.get('username')

    return dict(
        cart_count=cart_count,
        wishlist_count=wishlist_count,
        wishlist=wishlist,
        logged_in_user=logged_in_user
    )

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('customer/index.html', item=items)

@app.route('/product')
def products():
    q = request.args.get('q', '').strip()
    selected_categories = request.args.getlist('category')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort', '')

    filtered_items = items.copy()

    # Search filter
    if q:
        filtered_items = [
            itm for itm in filtered_items
            if q.lower() in itm['title'].lower() or q.lower() in itm['description'].lower()
        ]

    # Category filter
    if selected_categories:
        filtered_items = [
            itm for itm in filtered_items
            if itm['category'] in selected_categories
        ]

    # Price filter
    if min_price is not None:
        filtered_items = [itm for itm in filtered_items if itm['price'] >= min_price]
    if max_price is not None:
        filtered_items = [itm for itm in filtered_items if itm['price'] <= max_price]

    # Sorting
    if sort_by == 'low_high':
        filtered_items.sort(key=lambda x: x['price'])
    elif sort_by == 'high_low':
        filtered_items.sort(key=lambda x: x['price'], reverse=True)
    elif sort_by == 'rating':
        filtered_items.sort(key=lambda x: x['rating']['rate'], reverse=True)

    return render_template(
        'customer/products.html',
        item=filtered_items,
        current_q=q,
        current_categories=selected_categories,
        current_min_price=min_price,
        current_max_price=max_price,
        current_sort=sort_by
    )

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        contact_query = {
            "name": name,
            "email": email,
            "subject": subject,
            "message": message
        }
        save_contact(contact_query)

        # Notify via Telegram
        telegram_text = f"<b>✉️ NEW CONTACT INQUIRY RECEIVED</b>\n"
        telegram_text += f"<b>----------------------------------</b>\n\n"
        telegram_text += f"👤 <b>Name:</b> {name}\n"
        telegram_text += f"📧 <b>Email:</b> <code>{email}</code>\n"
        telegram_text += f"📝 <b>Subject:</b> {subject}\n\n"
        telegram_text += f"💬 <b>Message:</b>\n<i>{message}</i>"
        send_telegram_message(telegram_text)

        flash("Thank you! Your message has been sent successfully.", "success")
        return redirect(url_for('contact'))

    return render_template('customer/contact.html')

@app.route('/api/book_showroom', methods=['POST'])
def book_showroom():
    data = request.get_json() or {}
    name = data.get('name')
    phone = data.get('phone')
    service = data.get('service')
    advisor = data.get('advisor')
    date_val = data.get('date')
    time_slot = data.get('time')
    notes = data.get('notes', '')

    # Notify via Telegram
    telegram_text = f"<b>👑 NEW VIP SHOWROOM BOOKING</b>\n"
    telegram_text += f"<b>----------------------------------</b>\n\n"
    telegram_text += f"👤 <b>Client:</b> {name}\n"
    telegram_text += f"📞 <b>Phone:</b> <code>{phone}</code>\n"
    telegram_text += f"📅 <b>Date:</b> {date_val}\n"
    telegram_text += f"⏰ <b>Time:</b> {time_slot}\n"
    telegram_text += f"💎 <b>Service:</b> {service}\n"
    telegram_text += f"👔 <b>Advisor:</b> {advisor}\n"
    if notes:
        telegram_text += f"\n📝 <b>Special Requests:</b>\n<i>{notes}</i>"

    send_telegram_message(telegram_text)
    return jsonify({"success": true})


@app.route('/about')
def about():
    return render_template('customer/about.html')

# --- MOCK AUTHENTICATION SYSTEM ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username')
        password = request.form.get('password')

        users = load_users()
        # Check if username or email matches and password matches
        user_found = None
        for u_name, u_info in users.items():
            if (u_name == username_or_email or u_info.get('email') == username_or_email) and u_info.get('password') == password:
                user_found = u_name
                break

        if user_found:
            session['username'] = user_found
            flash(f"Welcome back, {user_found}!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username/email or password.", "error")
            return redirect(url_for('login'))

    return render_template('share/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('register'))

        users = load_users()
        if username in users:
            flash("Username already exists.", "error")
            return redirect(url_for('register'))
        
        # Check email duplicate
        if any(u.get('email') == email for u in users.values()):
            flash("Email already registered.", "error")
            return redirect(url_for('register'))

        users[username] = {
            "email": email,
            "password": password
        }
        save_users(users)

        session['username'] = username
        flash("Account created successfully! Welcome to the shop.", "success")
        return redirect(url_for('home'))

    return render_template('share/register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have logged out successfully.", "success")
    return redirect(url_for('home'))

# --- DYNAMIC WISHLIST ROUTING ---

@app.route('/favorites')
def favorites():
    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []

    wishlist_items = [
        item for item in items
        if item['id'] in wishlist
    ]
    return render_template('customer/wishlist.html', wishlist_items=wishlist_items)

@app.route('/add_to_wishlist/<int:item_id>', methods=['POST'])
def add_to_wishlist(item_id):
    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []

    if item_id not in wishlist:
        wishlist.append(item_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = make_response(json.dumps({'success': True, 'wishlist_count': len(wishlist)}))
        response.headers['Content-Type'] = 'application/json'
        response.set_cookie('wishlist', json.dumps(wishlist), max_age=60 * 60 * 24 * 7)
        return response

    response = make_response(redirect(request.referrer or url_for('products')))
    response.set_cookie('wishlist', json.dumps(wishlist), max_age=60 * 60 * 24 * 7)
    return response

@app.route('/remove_from_wishlist/<int:item_id>', methods=['POST'])
def remove_from_wishlist(item_id):
    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []

    if item_id in wishlist:
        wishlist.remove(item_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = make_response(json.dumps({'success': True, 'wishlist_count': len(wishlist)}))
        response.headers['Content-Type'] = 'application/json'
        response.set_cookie('wishlist', json.dumps(wishlist), max_age=60 * 60 * 24 * 7)
        return response

    response = make_response(redirect(request.referrer or url_for('favorites')))
    response.set_cookie('wishlist', json.dumps(wishlist), max_age=60 * 60 * 24 * 7)
    return response


# --- CART FUNCTIONALITY ---

@app.route('/view_product/<int:item_id>')
def view_product(item_id):
    current_item = next((item for item in items if item['id'] == item_id), None)
    if not current_item:
        return render_template('customer/404.html'), 404

    related_products = [
        item for item in items
        if item['category'] == current_item['category'] and item['id'] != item_id
    ][:4]  # Limit to 4 related items

    # Check if item is in user's wishlist
    wishlist_cookie = request.cookies.get('wishlist')
    wishlist = json.loads(wishlist_cookie) if wishlist_cookie else []
    in_wishlist = item_id in wishlist

    return render_template(
        'customer/view_product.html',
        item=current_item,
        related_products=related_products,
        in_wishlist=in_wishlist
    )

@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart[str_item_id] += 1
    else:
        cart[str_item_id] = 1

    # Fetch product title for flash message
    product = next((item for item in items if item['id'] == item_id), None)
    prod_title = product['title'][:20] + "..." if product else "Product"
    
    # Calculate new cart count
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
    response = make_response(redirect(request.referrer or url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

@app.route('/cart')
def cart():
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    cart_items = []
    total_price = 0

    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': round(item_total, 2)
            })

    return render_template(
        'customer/cart.html',
        cart_items=cart_items,
        total_price=round(total_price, 2)
    )

@app.route('/increase_cart/<int:item_id>', methods=['POST'])
def increase_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart[str_item_id] += 1

    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

@app.route('/decrease_cart/<int:item_id>', methods=['POST'])
def decrease_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        if cart[str_item_id] > 1:
            cart[str_item_id] -= 1
        else:
            cart.pop(str_item_id)

    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart.pop(str_item_id)

    flash("Item removed from cart.", "success")
    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

@app.route('/clear_cart')
def clear_cart():
    flash("Shopping cart cleared.", "success")
    response = make_response(redirect(url_for('cart')))
    response.delete_cookie('cart')
    return response

# --- CHECKOUT & ORDER ROUTING ---

@app.route('/checkout')
def checkout():
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else {}

    cart_items = []
    total_price = 0

    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': round(item_total, 2)
            })

    if not cart_items:
        flash("Your cart is empty. Please add items before checkout.", "error")
        return redirect(url_for('cart'))

    # Retrieve current user details if logged in
    user_email = ""
    username = session.get('username')
    if username:
        users = load_users()
        user_email = users.get(username, {}).get('email', '')

    return render_template(
        'customer/checkout.html',
        cart_items=cart_items,
        total_price=round(total_price, 2),
        buyer_username=username,
        buyer_email=user_email
    )

@app.route('/place_order', methods=['POST'])
def place_order():
    buyer_name = request.form.get('buyer_name')
    buyer_phone = request.form.get('buyer_phone')
    buyer_email = request.form.get('buyer_email')
    buyer_address = request.form.get('buyer_address')
    order_notes = request.form.get('order_notes', 'N/A')
    
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
        return redirect(url_for('cart'))

    item_list_text = ""
    total_price = 0

    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total
            item_list_text += f"📦 <b>{product['title'][:25]}...</b>\n"
            item_list_text += f"   └ Qty: {quantity} × ${product['price']:.2f} = <b>${item_total:.2f}</b>\n\n"

    # Generate unique order ID
    import random
    order_id = f"YS-{random.randint(100000, 999999)}"

    # Save order details in session temporarily to show on success screen
    session['last_order'] = {
        "order_id": order_id,
        "buyer_name": buyer_name,
        "buyer_phone": buyer_phone,
        "buyer_email": buyer_email,
        "buyer_address": buyer_address,
        "order_notes": order_notes,
        "payment_method": payment_display,
        "total_price": round(total_price, 2),
        "items_summary": [
            {
                "title": next((item['title'] for item in items if str(item['id']) == k), "Product"),
                "quantity": v,
                "price": next((item['price'] for item in items if str(item['id']) == k), 0.0)
            }
            for k, v in cart.items()
        ]
    }

    # Always save order details to orders.json
    username = session.get('username')
    import datetime
    timestamp = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    order_record = {
        "order_id": order_id,
        "timestamp": timestamp,
        "payment_method": payment_display,
        "total_price": round(total_price, 2),
        "buyer_name": buyer_name,
        "buyer_phone": buyer_phone,
        "buyer_email": buyer_email,
        "buyer_address": buyer_address,
        "order_notes": order_notes,
        "items": [
            {
                "title": next((item['title'] for item in items if str(item['id']) == k), "Product"),
                "quantity": v,
                "price": next((item['price'] for item in items if str(item['id']) == k), 0.0),
                "image": next((item['image'] for item in items if str(item['id']) == k), "")
            }
            for k, v in cart.items()
        ]
    }
    save_order(username, order_record)

    # Construct Telegram notification message
    telegram_text = f"<b>🔔 NEW ORDER RECEIVED ({payment_method.upper()})</b>\n"
    telegram_text += f"<b>----------------------------------</b>\n\n"
    telegram_text += f"👤 <b>Customer:</b> {buyer_name}\n"
    telegram_text += f"📞 <b>Phone:</b> <code>{buyer_phone}</code>\n"
    telegram_text += f"📧 <b>Email:</b> <code>{buyer_email}</code>\n"
    telegram_text += f"📍 <b>Address:</b> {buyer_address}\n"
    telegram_text += f"📝 <b>Notes:</b> <i>{order_notes}</i>\n\n"
    telegram_text += f"<b>🛒 ORDER ITEMS:</b>\n"
    telegram_text += item_list_text
    telegram_text += f"<b>----------------------------------</b>\n"
    telegram_text += f"💰 <b>TOTAL PAID: ${total_price:.2f} USD ({payment_display})</b>"
    send_telegram_message(telegram_text)


    # Redirect to success page and clear cart
    response = make_response(redirect(url_for('order_success')))
    response.delete_cookie('cart')
    return response

@app.route('/order_success')
def order_success():
    order = session.get('last_order')
    if not order:
        return redirect(url_for('home'))
    return render_template('customer/order_success.html', order=order)

@app.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        flash("Please log in to view your profile.", "error")
        return redirect(url_for('login'))
        
    # Get user email
    users = load_users()
    email = users.get(username, {}).get('email', 'N/A')
    
    # Load orders
    user_orders = load_orders(username)
    
    # Reverse so the latest order is at the top
    user_orders = list(reversed(user_orders))
    
    return render_template('customer/profile.html', username=username, email=email, orders=user_orders)

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('login'))
        
    username = session['username']
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_password or not new_password or not confirm_password:
        flash("All password fields are required.", "error")
        return redirect(url_for('profile'))
        
    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for('profile'))
        
    users = load_users()
    user_info = users.get(username)
    
    if not user_info or user_info.get('password') != current_password:
        flash("Incorrect current password.", "error")
        return redirect(url_for('profile'))
        
    # Update password
    users[username]['password'] = new_password
    save_users(users)
    
    flash("Your password has been updated successfully.", "success")
    return redirect(url_for('profile'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash("Please enter your email address.", "error")
            return redirect(url_for('forgot_password'))
            
        users = load_users()
        user_found = None
        username_found = None
        for username, u_info in users.items():
            if u_info.get('email') == email:
                user_found = u_info
                username_found = username
                break
                
        if username_found:
            # Generate a secure reset token
            token = secrets.token_urlsafe(32)
            RESET_TOKENS[token] = username_found
            
            # Construct reset URL (supporting proxy headers for live domains like Vercel)
            host = request.headers.get('X-Forwarded-Host') or request.headers.get('Host') or request.host
            proto = request.headers.get('X-Forwarded-Proto') or request.scheme
            base_url = f"{proto}://{host}"
            reset_url = base_url.rstrip('/') + url_for('reset_password', token=token)

            # Send real email
            send_reset_email(email, username_found, reset_url)

            
            # Log to console
            print(f"Password reset link generated for {username_found}: {reset_url}", flush=True)
            
            flash("If your email is registered, we have sent a reset link to it. Please check your inbox.", "success")
        else:
            # Show same success message to prevent user enumeration
            print(f"Password reset requested for unregistered email: {email}", flush=True)
            flash("If your email is registered, we have sent a reset link to it. Please check your inbox.", "success")
            
        return redirect(url_for('login'))
        
    return render_template('share/forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    username = RESET_TOKENS.get(token)
    if not username:
        flash("The reset link is invalid or has expired.", "error")
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or not confirm_password:
            flash("Please enter and confirm your new password.", "error")
            return render_template('share/reset_password.html')
            
        if new_password != confirm_password:
            flash("New passwords do not match.", "error")
            return render_template('share/reset_password.html')
            
        users = load_users()
        if username in users:
            users[username]['password'] = new_password
            save_users(users)
            # Remove used token
            RESET_TOKENS.pop(token, None)
            flash("Your password has been reset successfully. Please log in with your new password.", "success")
            return redirect(url_for('login'))
        else:
            flash("User not found.", "error")
            return redirect(url_for('login'))
            
    return render_template('share/reset_password.html')



def find_order_by_id(order_id):
    if not os.path.exists(ORDERS_FILE):
        return None, None
    try:
        with open(ORDERS_FILE, 'r') as f:
            orders = json.load(f)
        for user_key, user_orders in orders.items():
            for o in user_orders:
                if str(o.get('order_id')).strip().upper() == str(order_id).strip().upper():
                    return o, user_key
    except Exception as e:
        print(f"Error finding order: {e}")
    return None, None

def get_order_status(timestamp_str):
    try:
        import datetime
        order_time = datetime.datetime.strptime(timestamp_str, "%d %b %Y, %I:%M %p")
        now = datetime.datetime.now()
        diff = (now - order_time).total_seconds()
        if diff < 120: # 2 minutes
            return "Order Placed & Processing", 1
        elif diff < 600: # 10 minutes
            return "Showroom Packaging", 2
        elif diff < 3600: # 1 hour
            return "Dispatched & In Transit", 3
        else:
            return "Arrived & Delivered", 4
    except Exception:
        return "Dispatched & In Transit", 3

@app.route('/api/track_order/<order_id>')
def track_order_api(order_id):
    order, user_key = find_order_by_id(order_id)
    if order:
        status_text, status_code = get_order_status(order.get('timestamp', ''))
        return jsonify({
            "success": True,
            "order_id": order.get('order_id'),
            "buyer_name": order.get('buyer_name'),
            "timestamp": order.get('timestamp'),
            "total_price": order.get('total_price'),
            "items": order.get('items', []),
            "status_text": status_text,
            "status_code": status_code
        })
    else:
        return jsonify({
            "success": False,
            "message": f"Order ID '{order_id}' not found. Please verify the code and try again."
        })

@app.errorhandler(404)
def page_not_found(e):
    return render_template('customer/404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)