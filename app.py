import logging
import re
import uuid  # Pour générer des UUID
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort,g 
from config import Config  # Import de la configuration centralisée
from extensions import db, bcrypt, limiter  # Import des extensions
from auth_logs import log_auth_action, AuthLog  # Import de la fonction d'enregistrement des logs
from sqlalchemy.dialects.postgresql import UUID  # Pour le type UUID dans SQLAlchemy
from models.permissions import user_has_role, user_has_permission,IsAssignedTo, Role  # Gestion des rôles et permissions
from extensions import csrf
from forms import LoginForm, RegisterForm, LogoutForm


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
csrf.init_app(app)

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
    form = LogoutForm()  # Instancier le formulaire
    return render_template('index.html', form=form)

@app.context_processor
def inject_logout_form():
    return {"logout_form": LogoutForm()}


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
    if form.validate_on_submit():  # Vérification des champs avec WTForms
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            # Appliquer la limite uniquement si l'identifiant est incorrect
            return failed_login_attempt()

        # Connexion réussie, aucune limitation appliquée
        roles = db.session.query(Role.name).join(IsAssignedTo).filter(IsAssignedTo.user_id == user.id).all()
        session['user_id'] = user.id
        session['user_name'] = user.first_name
        session['roles'] = [role.name for role in roles]
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

    return render_template('login.html', form=form)  # Envoi du formulaire à la vue


# Définition d'une fonction pour limiter les échecs de connexion
@limiter.limit("5 per minute")
def failed_login_attempt():
    flash("Identifiants invalides.", "error")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():  # Vérification des champs avec WTForms
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        password = form.password.data

        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà enregistré.", "error")
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            email=email,
            password_hash=hashed_password,
            first_name=first_name,
            last_name=last_name
        )
        db.session.add(new_user)
        db.session.commit()

        # Attribution automatique du rôle "Visiteur"
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

    return render_template('register.html', form=form)





@app.route('/logout', methods=['POST'])
@login_required
def logout_user():
    form = LogoutForm()
    if form.validate_on_submit():  # Vérifie que le CSRF token est valide
        log_auth_action(
            user_id=session.get('user_id'),
            action_type="logout",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        session.clear()  # Supprime la session
        flash("Déconnexion réussie !", "success")
        return redirect(url_for('home'))

    flash("Erreur CSRF détectée", "error")
    return redirect(url_for('home'))





@app.route('/admin/roles')
@role_required('Admin')  # Seuls les admins peuvent voir cette page
def admin_roles():
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
        subquery_last_ip.label('last_ip')
    ).all()

    user_roles = {
        user_id: role_name for user_id, role_name in db.session.query(IsAssignedTo.user_id, Role.name).join(Role).all()
    }

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

    roles = Role.query.all()
    return render_template('admin.html', users=users_list, roles=roles)


@app.route('/edit_robot')
@role_required('Roboticien')
def edit_robot():
    return render_template('edit_robot.html')




@app.route('/assign_role', methods=['POST'])
@role_required('Admin')
def assign_role():
    user_id = request.form.get('user_id')
    role_id = request.form.get('role_id')

    if not user_id or not role_id:
        flash("Données invalides", "error")
        logger.warning(f"Attribution de rôle échouée : user_id ou role_id manquant. user_id={user_id}, role_id={role_id}")
        return redirect(url_for('admin_roles'))

    try:
        role = Role.query.get(role_id)
        if not role:
            flash("Rôle invalide", "error")
            logger.warning(f"Tentative d'attribution d'un rôle inexistant : role_id={role_id}")
            return redirect(url_for('admin_roles'))

        db.session.query(IsAssignedTo).filter_by(user_id=user_id).delete()
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
