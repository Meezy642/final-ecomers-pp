from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User
from models.product import Product
from models.order import Order
from models.contact import Contact
