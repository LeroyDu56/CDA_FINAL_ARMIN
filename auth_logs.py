from extensions import db
from sqlalchemy.dialects.postgresql import UUID, INET
from datetime import datetime

class AuthLog(db.Model):
    __tablename__ = 'auth_logs'

    log_id = db.Column(db.Integer, primary_key=True)  # Clé primaire auto-incrémentée
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)  # UUID lié à users.user_id
    action_type = db.Column(db.String(20), nullable=False)  # Type d'action (ex. : login, logout)
    ip_address = db.Column(INET, nullable=True)  # Adresse IP
    user_agent = db.Column(db.String(255), nullable=True)  # Informations User-Agent
    timestamp = db.Column(
        "_timestamp",  # Mappage explicite pour la colonne _timestamp
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f"<AuthLog(user_id={self.user_id}, action_type='{self.action_type}', timestamp={self.timestamp})>"


# Fonction pour enregistrer un log dans la base de données ET dans un fichier texte
def log_auth_action(user_id, action_type, ip_address=None, user_agent=None):
    """
    Enregistre une action utilisateur dans la table auth_logs ET dans un fichier texte.
    """
    try:
        # Enregistrement dans la base de données
        new_log = AuthLog(
            user_id=user_id,
            action_type=action_type,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(new_log)
        db.session.commit()

        # Écriture dans le fichier texte
        write_log_to_file(user_id, action_type, ip_address, user_agent)
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de l'enregistrement du log : {e}")
        raise e

# Fonction pour écrire dans le fichier texte
def write_log_to_file(user_id, action_type, ip_address=None, user_agent=None):
    """
    Écrit les informations de l'action utilisateur dans un fichier texte.
    """
    LOG_FILE_PATH = "auth_logs.txt"
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
            log_file.write("-----------------------------------------------------\n")
            log_file.write(f"Date/Heure : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"User ID    : {user_id}\n")
            log_file.write(f"Action     : {action_type}\n")
            log_file.write(f"IP Address : {ip_address or 'Non spécifiée'}\n")
            log_file.write(f"User Agent : {user_agent or 'Non spécifié'}\n")
            log_file.write("-----------------------------------------------------\n\n")
    except Exception as e:
        print(f"Erreur lors de l'écriture dans le fichier texte : {e}")
        raise e
