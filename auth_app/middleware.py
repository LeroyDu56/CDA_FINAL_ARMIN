from django.utils import timezone
from .models import LoginAttempt
import random

class LoginAttemptsCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Probabilité de 1% pour nettoyer les anciennes tentatives
        # Cela évite de faire cette opération à chaque requête
        if random.random() < 0.01:
            LoginAttempt.clear_old_attempts()
            
        response = self.get_response(request)
        return response