import json
from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from extensions import db
from models.product import Product
from models.order import Order
from models.contact import Contact
from items import items
from . import front_bp

@front_bp.route("/")
def home():
    prods = Product.query.order_by(Product.id.asc()).all()
    if prods:
        product_list = [p.to_dict() for p in prods]
    else:
        product_list = items
    return render_template("customer/index.html", item=product_list, products=product_list)

@front_bp.route("/products")
def products():
    category = request.args.get("category")
    search_query = request.args.get("search", "").strip()

    query = Product.query
    if category and category != "all":
        query = query.filter_by(category=category)
    if search_query:
        query = query.filter(Product.title.ilike(f"%{search_query}%"))

    prods = query.all()
    if prods:
        product_list = [p.to_dict() for p in prods]
    else:
        product_list = items
        if category and category != "all":
            product_list = [p for p in product_list if p.get("category") == category]
        if search_query:
            product_list = [p for p in product_list if search_query.lower() in p.get("title", "").lower()]

    categories = [c[0] for c in db.session.query(Product.category).distinct().all() if c[0]]
    if not categories:
        categories = list(set([p.get("category", "") for p in items]))
    return render_template("customer/products.html", item=product_list, products=product_list, categories=categories, current_category=category)

@front_bp.route("/product/<int:item_id>")
def product_detail(item_id):
    product = Product.query.get(item_id)
    if not product:
        product = next((p for p in items if p.get("id") == item_id), None)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("front.products"))
    return render_template("customer/view_product.html", product=product)

@front_bp.route("/cart")
def cart():
    cart_cookie = request.cookies.get("cart")
    cart_data = json.loads(cart_cookie) if cart_cookie else {}
    cart_items = []
    total = 0.0

    for item_id_str, qty in cart_data.items():
        try:
            item_id = int(item_id_str)
            prod = Product.query.get(item_id)
            if not prod:
                prod = next((p for p in items if p.get("id") == item_id), None)
            if prod:
                price = float(prod.price if hasattr(prod, "price") else prod.get("price", 0))
                title = prod.title if hasattr(prod, "title") else prod.get("title", "")
                image = prod.image if hasattr(prod, "image") else prod.get("image", "")
                subtotal = price * qty
                total += subtotal
                cart_items.append({
                    "id": item_id,
                    "title": title,
                    "price": price,
                    "image": image,
                    "quantity": qty,
                    "subtotal": subtotal
                })
        except Exception:
            continue

    return render_template("customer/cart.html", cart_items=cart_items, total=total)

@front_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        flash("Order placed successfully!", "success")
        resp = make_response(redirect(url_for("front.home")))
        resp.set_cookie("cart", "", expires=0)
        return resp
    return render_template("customer/checkout.html")
