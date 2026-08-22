import json
from models import db

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(80), nullable=True)
    buyer_name = db.Column(db.String(100), nullable=True)
    buyer_phone = db.Column(db.String(50), nullable=True)
    buyer_email = db.Column(db.String(120), nullable=True)
    buyer_address = db.Column(db.Text, nullable=True)
    order_notes = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(100), nullable=True)
    total_price = db.Column(db.Float, nullable=False, default=0.0)
    items_json = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        items = []
        if self.items_json:
            try:
                items = json.loads(self.items_json)
            except Exception:
                items = []
        return {
            "order_id": self.order_id,
            "timestamp": self.timestamp or '',
            "payment_method": self.payment_method or 'Bakong KHQR - Paid',
            "total_price": self.total_price,
            "buyer_name": self.buyer_name or '',
            "buyer_phone": self.buyer_phone or '',
            "buyer_email": self.buyer_email or '',
            "buyer_address": self.buyer_address or '',
            "order_notes": self.order_notes or '',
            "items": items
        }
