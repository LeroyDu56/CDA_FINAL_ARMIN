import logging
import re
import uuid  # Pour générer des UUID
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from config import Config  # Import de la configuration centralisée
from extensions import db, bcrypt, limiter  # Import des extensions
from auth_logs import log_auth_action, AuthLog  # Import de la fonction d'enregistrement des logs
from sqlalchemy.dialects.postgresql import UUID  # Pour le type UUID dans SQLAlchemy
from models.permissions import user_has_role, user_has_permission,IsAssignedTo, Role  # Gestion des rôles et permissions



# =============================================================================
# CONFIGURATION DE L'APPLICATION
# =============================================================================

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,  # Niveau minimal de log
    format="%(asctime)s [%(levelname)s] %(message)s",  # Format des messages de log
    handlers=[
        logging.FileHandler("app.log"),  # Sauvegarde les logs dans un fichier app.log
        logging.StreamHandler()  # Affiche les logs dans le terminal
    ]
)

# Créez un logger spécifique pour l'application
logger = logging.getLogger(__name__)

# Configuration de l'application Flask
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)


# Initialisation des extensions Flask
db.init_app(app)
bcrypt.init_app(app)
limiter.init_app(app)


# =============================================================================
# MODÈLE UTILISATEUR
# =============================================================================

class User(db.Model):
    __tablename__ = 'users'

    # Les colonnes de la table
    id = db.Column("user_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # UUID comme clé primaire
    email = db.Column(db.String(255), unique=True, nullable=False)  # Email (255 caractères max)
    password_hash = db.Column(db.String(255), nullable=False)  # Hash du mot de passe
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # Statut actif/inactif
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)  # Date de création
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)  # Dernière connexion
    first_name = db.Column(db.String(50), nullable=True)  # Prénom
    last_name = db.Column(db.String(50), nullable=True)  # Nom

    # Méthode pour vérifier le mot de passe
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    # Représentation lisible d'un utilisateur
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', active={self.is_active})>"

# =============================================================================
# VALIDATION DES ENTRÉES
# =============================================================================

def is_valid_email(email):
    """Vérifie que l'email respecte un format de base."""
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None

def is_valid_password(password):
    """Vérifie que le mot de passe contient au moins 8 caractères."""
    return len(password) >= 8

# =============================================================================
# DÉCORATEURS POUR LES DROITS D'ACCÈS
# =============================================================================

def login_required(f):
    """
    Décorateur pour vérifier si l'utilisateur est connecté.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    """
    Décorateur pour restreindre l'accès à une route en fonction d'un rôle.
    """
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_has_role(user_id, role_name):
                abort(403)  # Accès refusé
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def permission_required(permission_code):
    """
    Décorateur pour restreindre l'accès à une route en fonction d'une permission.
    """
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_has_permission(user_id, permission_code):
                abort(403)  # Accès refusé
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# =============================================================================
# ROUTES DE L'APPLICATION
# =============================================================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Email et mot de passe requis.", "error")
            return redirect(url_for('login'))

        try:
            user = User.query.filter_by(email=email).first()
            if not user or not user.check_password(password):
                flash("Identifiants invalides.", "error")
                return redirect(url_for('login'))

            # Vérifier tous les rôles associés
            roles = db.session.query(Role.name).join(IsAssignedTo).filter(IsAssignedTo.user_id == user.id).all()
            session['user_id'] = user.id
            session['user_name'] = user.first_name
            session['roles'] = [role.name for role in roles]  # Liste des rôles

            # Vérifier si l'utilisateur est admin
            session['is_admin'] = 'Admin' in session['roles']

            # Enregistrement du log
            log_auth_action(
                user_id=user.id,
                action_type="login",
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

            flash("Connexion réussie !", "success")
            return redirect(url_for('home'))
        except Exception as e:
            logger.error(f"Erreur lors de la connexion : {e}")
            flash("Une erreur est survenue. Veuillez réessayer.", "error")
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')  # Champ pour confirmer le mot de passe
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        if not all([email, password, confirm_password, first_name, last_name]):
            flash("Tous les champs sont requis.", "error")
            return redirect(url_for('register'))

        if not is_valid_email(email):
            flash("Format d'email invalide.", "error")
            return redirect(url_for('register'))

        if not is_valid_password(password):
            flash("Le mot de passe doit contenir au moins 8 caractères.", "error")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "error")
            return redirect(url_for('register'))

        try:
            if User.query.filter_by(email=email).first():
                flash("Cet email est déjà enregistré.", "error")
                return redirect(url_for('register'))

            hashed_password = bcrypt.generate_password_hash(password, rounds=14).decode('utf-8')
            new_user = User(
                email=email,
                password_hash=hashed_password,
                first_name=first_name,
                last_name=last_name
            )
            db.session.add(new_user)
            db.session.commit()

            # Attribuer automatiquement le rôle "Visiteur"
            visitor_role = Role.query.filter_by(name="Visiteur").first()
            if visitor_role:
                is_assigned_to = IsAssignedTo(user_id=new_user.id, role_id=visitor_role.role_id)
                db.session.add(is_assigned_to)
                db.session.commit()

            # Enregistrement du log
            log_auth_action(
                user_id=new_user.id,
                action_type="register",
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

            session['user_id'] = new_user.id
            session['user_name'] = new_user.first_name
            flash("Inscription réussie !", "success")
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            logger.error("Erreur lors de l'inscription : %s", e)
            flash("Une erreur est survenue. Veuillez réessayer.", "error")
            return redirect(url_for('register'))
    return render_template('register.html')





@app.route('/logout', methods=['POST'])
@login_required
def logout_user():
    # Enregistrement du log
    log_auth_action(
        user_id=session.get('user_id'),
        action_type="logout",
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    session.clear()  # Réinitialise complètement la session
    flash("Déconnexion réussie !", "success")
    return redirect(url_for('home'))





@app.route('/admin/roles')
@role_required('Admin')  # Seuls les admins peuvent voir cette page
def admin_roles():
    # Récupérer tous les utilisateurs et leurs dernières IP
    subquery_last_ip = (
        db.session.query(AuthLog.ip_address)
        .filter(AuthLog.user_id == User.id)
        .order_by(AuthLog.timestamp.desc())
        .limit(1)
        .scalar_subquery()
    )

    users = db.session.query(
        User.id,
        User.email,
        User.first_name,
        User.last_name,
        subquery_last_ip.label('last_ip')  # Pas besoin de coalesce ici
    ).all()

    # Récupérer leurs rôles actuels
    user_roles = {
        user_id: role_name for user_id, role_name in db.session.query(IsAssignedTo.user_id, Role.name).join(Role).all()
    }

    # Ajouter les rôles actuels aux utilisateurs
    users_list = []
    for user in users:
        users_list.append({
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "last_ip": user.last_ip if user.last_ip else "Non disponible",
            "current_role": user_roles.get(user.id, "Aucun")
        })

    # Récupérer tous les rôles possibles
    roles = Role.query.all()

    return render_template('admin.html', users=users_list, roles=roles)





@app.route('/edit_robot')
@role_required('Roboticien')
def edit_robot():
    return render_template('edit_robot.html')




@app.route('/assign_role', methods=['POST'])
@role_required('Admin')  # Seuls les admins peuvent assigner des rôles
def assign_role():
    user_id = request.form.get('user_id')
    role_id = request.form.get('role_id')

    if not user_id or not role_id:
        flash("Données invalides", "error")
        logger.warning(f"Attribution de rôle échouée : user_id ou role_id manquant. user_id={user_id}, role_id={role_id}")
        return redirect(url_for('admin_roles'))

    try:
        # Vérification que le rôle existe
        role = Role.query.get(role_id)
        if not role:
            flash("Rôle invalide", "error")
            logger.warning(f"Tentative d'attribution d'un rôle inexistant : role_id={role_id}")
            return redirect(url_for('admin_roles'))

        # Supprimer les anciens rôles de cet utilisateur
        db.session.query(IsAssignedTo).filter_by(user_id=user_id).delete()

        # Ajouter le nouveau rôle
        new_role = IsAssignedTo(user_id=user_id, role_id=role_id)
        db.session.add(new_role)
        db.session.commit()

        flash("Rôle mis à jour avec succès", "success")
        logger.info(f"Rôle {role.name} attribué avec succès à l'utilisateur {user_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'attribution du rôle : {e}")
        flash("Erreur lors de l'attribution du rôle", "error")

    return redirect(url_for('admin_roles'))



# =============================================================================
# GESTION DES ERREURS
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# =============================================================================
# DÉMARRAGE DE L'APPLICATION
# =============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Création des tables si elles n'existent pas
    app.run(debug=False, host='0.0.0.0', port=3000)
