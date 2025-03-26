import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# --- Manager pour le modèle utilisateur personnalisé ---
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'email est requis")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Hashage du mot de passe
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superuser doit avoir is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

# --- Modèle utilisateur personnalisé ---
class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Pour accès à l'interface admin
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)

    # Relation many-to-many avec Role via la table intermédiaire IsAssignedTo
    roles = models.ManyToManyField('Role', through='IsAssignedTo', related_name='users')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Pas de champs obligatoires supplémentaires

    objects = CustomUserManager()

    def __str__(self):
        return self.email

# --- Modèle pour les logs d'authentification ---
class AuthLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    action_type = models.CharField(max_length=20)
    ip_address = models.CharField(max_length=45, null=True, blank=True)  # Pour IPv4 et IPv6
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action_type} at {self.timestamp}"

# --- Modèle pour les permissions ---
class Permission(models.Model):
    permission_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.code

# --- Modèle pour les rôles ---
class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=50, null=True, blank=True)
    # Relation many-to-many avec Permission via le modèle intermédiaire Grant
    permissions = models.ManyToManyField(Permission, through='Grant', related_name='roles')

    def __str__(self):
        return self.name

# --- Table intermédiaire entre Role et Permission (Grants) ---
class Grant(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role} -> {self.permission}"

# --- Table intermédiaire entre User et Role (IsAssignedTo) ---
class IsAssignedTo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user} assigned to {self.role}"

class ServiceTask(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('urgent', 'Urgente')
    ]

    STATUS_CHOICES = [
        ('pending', 'À faire'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('archived', 'Archivée')  # Ajout d'un nouveau statut pour les tâches archivées
    ]

    host = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Nouveau champ pour le client
    client = models.CharField(max_length=255, blank=True, default="Non spécifié")

    def __str__(self):
        return f"{self.title} - {self.host}"

    def get_priority_display(self):
        return dict(self.PRIORITY_CHOICES).get(self.priority, '')

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, '')