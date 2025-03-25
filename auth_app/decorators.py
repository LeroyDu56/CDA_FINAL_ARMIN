from django.http import HttpResponseForbidden
from functools import wraps

def role_required(allowed_roles):
    """
    Décorateur pour restreindre l'accès aux utilisateurs ayant certains rôles.
    :param allowed_roles: Liste des noms de rôles autorisés.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Vous devez être connecté pour accéder à cette page.")

            # Vérifie si l'utilisateur a un des rôles autorisés
            user_roles = request.user.roles.values_list('name', flat=True)
            if not any(role in allowed_roles for role in user_roles):
                return HttpResponseForbidden("Vous n'avez pas les permissions nécessaires pour accéder à cette page.")

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator