from flask import Blueprint

front_bp = Blueprint('front', __name__)

from . import auth, store
