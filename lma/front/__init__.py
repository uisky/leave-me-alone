from flask import Blueprint

mod = Blueprint('front', __name__, url_prefix='')

from . import views
