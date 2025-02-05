import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env (uniquement ici)
load_dotenv()

class Config:
    """Configuration pour Flask."""
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("La variable d'environnement SECRET_KEY n'est pas définie !")
    
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("La variable d'environnement DATABASE_URL n'est pas définie !")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Sécurisation des cookies (HTTPONLY, SAMESITE, etc.)
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "development"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DBConfig:
    """Configuration pour la connexion à la base de données via psycopg2."""
    HOST = os.getenv("DB_HOST")
    PORT = os.getenv("DB_PORT")
    DATABASE = os.getenv("DB_NAME")
    USER = os.getenv("DB_USER")
    PASSWORD = os.getenv("DB_PASSWORD")
    if not all([HOST, PORT, DATABASE, USER, PASSWORD]):
        raise ValueError("Une ou plusieurs variables d'environnement pour la DB ne sont pas définies.")
