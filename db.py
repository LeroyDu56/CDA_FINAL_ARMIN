import psycopg2
from psycopg2.extras import RealDictCursor
from config import DBConfig  # Import de la configuration DB centralisée

def get_connection():
    try:
        conn = psycopg2.connect(
            host=DBConfig.HOST,
            port=DBConfig.PORT,
            database=DBConfig.DATABASE,
            user=DBConfig.USER,
            password=DBConfig.PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ Erreur lors de la connexion à la base de données : {e}")
        raise e
