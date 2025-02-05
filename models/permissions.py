from extensions import db
from sqlalchemy.dialects.postgresql import UUID
import logging

logger = logging.getLogger(__name__)
# Modèle pour la table des rôles
class Role(db.Model):
    __tablename__ = 'roles'

    role_id = db.Column(db.Integer, primary_key=True)  # ID du rôle
    name = db.Column(db.String(50), unique=True, nullable=False)  # Nom du rôle
    description = db.Column(db.String(50), nullable=True)  # Description du rôle

    # Relation avec les permissions via grants
    permissions = db.relationship('Permission', secondary='grants', backref='roles')

    def __repr__(self):
        return f"<Role(name={self.name})>"

# Modèle pour la table des permissions
class Permission(db.Model):
    __tablename__ = 'permissions'

    permission_id = db.Column(db.Integer, primary_key=True)  # ID de la permission
    code = db.Column(db.String(50), unique=True, nullable=False)  # Code de la permission
    description = db.Column(db.String(50), nullable=True)  # Description de la permission

    def __repr__(self):
        return f"<Permission(code={self.code})>"

# Table pivot pour associer les rôles aux permissions
class Grant(db.Model):
    __tablename__ = 'grants'

    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id', ondelete='CASCADE'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.permission_id', ondelete='CASCADE'), primary_key=True)

# Table pivot pour associer les utilisateurs aux rôles
class IsAssignedTo(db.Model):
    __tablename__ = 'is_assigned_to'

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id', ondelete='CASCADE'), primary_key=True)

def user_has_role(user_id, role_name):
    try:
        return db.session.query(IsAssignedTo).join(Role).filter(
            IsAssignedTo.user_id == user_id,
            Role.name == role_name
        ).count() > 0
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du rôle {role_name} pour l'utilisateur {user_id}: {e}")
        return False

def user_has_permission(user_id, permission_code):
    try:
        return db.session.query(IsAssignedTo).join(Role).join(Grant).join(Permission).filter(
            IsAssignedTo.user_id == user_id,
            Permission.code == permission_code
        ).count() > 0
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de la permission {permission_code} pour l'utilisateur {user_id}: {e}")
        return False
