from flask import Blueprint

mod = Blueprint('projects', __name__, url_prefix='/projects')

from . import views
