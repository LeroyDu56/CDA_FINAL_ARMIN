from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialisation des extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
