from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default='customer')
    name = db.Column(db.String(80), nullable=True)
    profile_image = db.Column(db.String(255), default='no-profile.png')
    create_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def image(self):
        return self.profile_image

    @image.setter
    def image(self, value):
        self.profile_image = value

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        if not self.password:
            return False
        if self.password.startswith('scrypt:') or self.password.startswith('pbkdf2:') or self.password.startswith('$'):
            try:
                return check_password_hash(self.password, password)
            except Exception:
                return False
        return self.password == password

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone_number': self.phone_number,
            'role': self.role,
            'name': self.name,
            'image': self.profile_image or 'no-profile.png',
            'profile_image': self.profile_image or 'no-profile.png',
            'create_at': self.create_at.strftime("%d %b %Y, %I:%M %p") if self.create_at else ''
        }
