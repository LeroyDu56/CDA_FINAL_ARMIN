from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Votre email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Votre mot de passe'}))

class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Prénom',
            # Ajoutez d'autres attributs si nécessaire (class CSS, etc.)
        }),
        error_messages={
            'required': 'Veuillez saisir votre prénom.',
        }
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Nom',
        }),
        error_messages={
            'required': 'Veuillez saisir votre nom.',
        }
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Votre email',
        }),
        error_messages={
            'required': 'Veuillez saisir une adresse email.',
            'invalid': 'L’adresse email est invalide.',
        }
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')