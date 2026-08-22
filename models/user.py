from datetime import datetime
from models import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default='customer')
    name = db.Column(db.String(80), nullable=True)
    profile_image = db.Column(db.String(255), default='no-profile.png')
    create_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone_number': self.phone_number,
            'role': self.role,
            'name': self.name,
            'profile_image': self.profile_image or 'no-profile.png',
            'create_at': self.create_at.strftime("%d %b %Y, %I:%M %p") if self.create_at else ''
        }
