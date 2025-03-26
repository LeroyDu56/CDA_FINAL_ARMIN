# auth_app/views.py
import requests
import os
from datetime import datetime
from django.db.models import Q, Case, When, Value, IntegerField
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import HttpResponseForbidden, JsonResponse
from .forms import LoginForm, RegisterForm
from .models import User, Role, AuthLog, ServiceTask
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.influx import get_hosts_status
from .decorators import role_required

def index(request):
    # Page d'accueil
    user_is_admin = False
    user_is_roboticien = False
    user_is_visitor = False
    user_is_client = False
    notifications = []

    if request.user.is_authenticated:
        user_is_admin = request.user.roles.filter(name='Admin').exists()
        user_is_roboticien = request.user.roles.filter(name='Roboticien').exists()
        user_is_visitor = request.user.roles.filter(name='Visiteur').exists()
        user_is_client = request.user.roles.filter(name='Client').exists()

        # Ajouter la récupération des notifications GitHub
        try:
            github_owner = os.environ.get('GITHUB_REPO_OWNER')
            github_repo = os.environ.get('GITHUB_REPO_NAME')
            github_updates = get_github_commits(github_owner, github_repo, count=2)

            for update in github_updates:
                notifications.append({
                    'title': update['title'],
                    'content': update['content'],
                    'date': update['date'].strftime("%d/%m/%Y %H:%M"),
                    'priority': update['priority'],
                    'url': update['url']
                })
        except Exception as e:
            notifications = [{
                'title': 'Impossible de récupérer les mises à jour',
                'content': 'Un problème est survenu lors de la récupération des mises à jour depuis GitHub.',
                'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'priority': 'medium'
            }]
            print(f"Erreur lors de la récupération des commits GitHub: {e}")

    # Récupérer les statistiques des robots depuis get_hosts_status
    try:
        from utils.influx import get_hosts_status
        hosts_status = get_hosts_status() or {}
        robots_count = len(hosts_status)
        active_robots = sum(1 for status in hosts_status.values() if status)
    except Exception as e:
        print(f"Erreur lors de la récupération des statistiques des robots: {e}")
        robots_count = '--'
        active_robots = '--'

    # Récupérer les statistiques des tâches SAV
    try:
        # Tâches à faire (pending)
        pending_tasks_count = ServiceTask.objects.filter(
            status='pending'
        ).count()

        # Tâches en cours (in_progress)
        in_progress_tasks_count = ServiceTask.objects.filter(
            status='in_progress'
        ).count()
    except Exception as e:
        print(f"Erreur lors de la récupération des statistiques des tâches: {e}")
        pending_tasks_count = 0
        in_progress_tasks_count = 0

    # Si l'utilisateur est un visiteur ou client, afficher "XX" au lieu des valeurs réelles
    if user_is_visitor or user_is_client:
        robots_count = "XX"
        active_robots = "XX"
        pending_tasks_count = "XX"
        in_progress_tasks_count = "XX"

    context = {
        'user_is_admin': user_is_admin,
        'user_is_roboticien': user_is_roboticien,
        'user_is_visitor': user_is_visitor,
        'user_is_client': user_is_client,
        'notifications': notifications,
        'robots_count': robots_count if robots_count != '--' else 0,
        'active_robots': active_robots if active_robots != '--' else 0,
        'alerts_count': 0,
        'pending_tasks_count': pending_tasks_count,  # Tâches à faire
        'in_progress_tasks_count': in_progress_tasks_count,  # Tâches en cours
    }

    return render(request, 'index.html', context)

def login_view(request):
    """Vue de connexion"""
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                AuthLog.objects.create(
                    user=user,
                    action_type="login",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
                messages.success(request, "Connexion réussie !")
                return redirect('index')
            else:
                messages.error(request, "Identifiants invalides.")
        else:
            messages.error(request, "Formulaire invalide.")
    else:
        form = LoginForm()

    user_is_admin = request.user.is_authenticated and request.user.roles.filter(name='Admin').exists()
    return render(request, 'login.html', {
        'form': form,
        'user_is_admin': user_is_admin
    })

def register_view(request):
    """Vue d'inscription sans usage de messages flash pour les erreurs."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            # Rôle visiteur
            try:
                visitor_role = Role.objects.get(name="Visiteur")
                user.roles.add(visitor_role)
            except Role.DoesNotExist:
                pass

            # Log d'inscription
            AuthLog.objects.create(
                user=user,
                action_type="register",
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            # Succès
            messages.success(request, "Inscription réussie !")
            login(request, user)
            return redirect('index')
        else:
            # NE PAS faire messages.error(...) ici.
            pass
            # Le formulaire va contenir les erreurs
            # qu'on affichera directement dans le template.
    else:
        form = RegisterForm()

    user_is_admin = request.user.is_authenticated and request.user.roles.filter(name='Admin').exists()
    return render(request, 'register.html', {
        'form': form,
        'user_is_admin': user_is_admin
    })


@login_required
def logout_view(request):
    """Vue de déconnexion"""
    if request.method == 'POST':
        AuthLog.objects.create(
            user=request.user,
            action_type="logout",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        logout(request)
        messages.success(request, "Déconnexion réussie !")
        return redirect('index')
    else:
        return HttpResponseForbidden("Méthode non autorisée.")

@login_required
@role_required(['Admin'])
def admin_roles_view(request):
    """Vue pour gérer les rôles (réservée aux admins)"""
    email = request.GET.get('email', '')
    first_name = request.GET.get('first_name', '')
    last_name = request.GET.get('last_name', '')
    role = request.GET.get('role', '')

    query = User.objects.all()
    if email:
        query = query.filter(email__icontains=email)
    if first_name:
        query = query.filter(first_name__icontains=first_name)
    if last_name:
        query = query.filter(last_name__icontains=last_name)
    if role:
        query = query.filter(roles__name__icontains=role)

    # Construire la liste enrichie
    users_data = []
    for u in query.distinct():
        last_log = AuthLog.objects.filter(user=u).order_by('-timestamp').first()
        last_ip = last_log.ip_address if last_log else "Non disponible"
        users_data.append({
            'user_id': u.user_id,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'last_ip': last_ip,
            'roles': u.roles.all(),
        })

    roles = Role.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role_id = request.POST.get('role_id')
        try:
            user_obj = User.objects.get(user_id=user_id)
            role_obj = Role.objects.get(role_id=role_id)
            user_obj.roles.clear()
            user_obj.roles.add(role_obj)
            messages.success(request, "Rôle mis à jour avec succès")
        except Exception:
            messages.error(request, "Erreur lors de l'attribution du rôle")

    return render(request, 'admin.html', {
        'users': users_data,
        'roles': roles,
        'user_is_admin': True,
    })

# Modification de la fonction robot_list_view dans views.py
@login_required
@role_required(['Admin', 'Roboticien'])
def robot_list_view(request):
    """Vue pour afficher la liste des robots"""
    user_is_admin = request.user.roles.filter(name='Admin').exists()
    user_is_roboticien = request.user.roles.filter(name='Roboticien').exists()

    # Récupérer le dict {host: is_fresh}
    basic_hosts_status = get_hosts_status() or {}

    # Récupérer les informations d'adresse IP avec débogage
    from utils.influx import get_host_ip_info
    print("\n\n=== DÉBOGAGE ROBOT_LIST_VIEW ===")
    print(f"Nombre d'hôtes trouvés: {len(basic_hosts_status)}")
    print(f"Hôtes: {', '.join(basic_hosts_status.keys())}")
    
    ip_info = get_host_ip_info()
    
    print(f"Informations IP récupérées pour {len(ip_info)} hôtes")
    print("=== FIN DÉBOGAGE ROBOT_LIST_VIEW ===\n\n")

    # Créer un dictionnaire enrichi avec plus d'informations
    hosts_status = {}

    for host, is_fresh in basic_hosts_status.items():
        # Récupérer l'IP
        ip = ip_info.get(host, {}).get('ip', "Non spécifiée")

        # Déterminer le client (si cette information est disponible)
        client = "Non spécifié"  # Valeur par défaut

        # Si vous avez un moyen de déterminer le client, utilisez-le ici
        host_tasks = ServiceTask.objects.filter(host=host).first()
        if host_tasks and hasattr(host_tasks, 'client') and host_tasks.client:
            client = host_tasks.client

        hosts_status[host] = {
            'is_fresh': is_fresh,
            'client': client,
            'ip': ip
        }

    return render(request, 'robot_list.html', {
        'user_is_admin': user_is_admin,
        'user_is_roboticien': user_is_roboticien,
        'hosts_status': hosts_status,
    })

@login_required
@role_required(['Admin', 'Roboticien'])
def host_detail_view(request, host):
    """Vue pour afficher les détails d'un hôte"""
    from utils.influx import get_hosts_status, get_last_connection_time
    from datetime import datetime, timezone

    # Traitement du formulaire d'ajout de tâche SAV
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority')
        status = request.POST.get('status')

        if title and description:
            try:
                # Créer une nouvelle tâche SAV
                ServiceTask.objects.create(
                    host=host,  # Utilisez directement la chaîne host
                    title=title,
                    description=description,
                    priority=priority,
                    status=status,
                    # Ne pas inclure created_by si ce champ n'existe pas dans votre modèle
                )
                messages.success(request, "Tâche SAV ajoutée avec succès.")
                return redirect('host_detail', host=host)
            except Exception as e:
                messages.error(request, f"Erreur lors de l'ajout de la tâche: {str(e)}")
                print(f"Erreur lors de l'ajout de la tâche: {str(e)}")
        else:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")

    # Récupérer les informations de l'hôte
    hosts_status = get_hosts_status() or {}
    is_host_active = hosts_status.get(host, False)
    last_connection_time = get_last_connection_time(host)

    # Formater le timestamp pour JavaScript
    last_connection_timestamp = last_connection_time.isoformat() if last_connection_time else ""

    # Déterminer l'affichage de la dernière connexion
    if is_host_active:
        last_connection_display = "Connecté actuellement"
    elif last_connection_time:
        now = datetime.now(timezone.utc)
        time_diff = now - last_connection_time

        if time_diff.days > 30:
            last_connection_display = f"Dernière connexion le {last_connection_time.strftime('%d/%m/%Y')}"
        elif time_diff.days > 0:
            last_connection_display = f"Il y a {time_diff.days} jour{'s' if time_diff.days > 1 else ''}"
        elif time_diff.seconds // 3600 > 0:
            hours = time_diff.seconds // 3600
            last_connection_display = f"Il y a {hours} heure{'s' if hours > 1 else ''}"
        elif time_diff.seconds // 60 > 0:
            minutes = time_diff.seconds // 60
            last_connection_display = f"Il y a {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            last_connection_display = "Il y a quelques secondes"
    else:
        last_connection_display = "Non disponible"

    # Vérification des rôles
    user_is_admin = request.user.roles.filter(name='Admin').exists()
    user_is_roboticien = request.user.roles.filter(name='Roboticien').exists()

    # Récupérer les tâches SAV pour cet hôte, en excluant les tâches archivées
    service_tasks = ServiceTask.objects.filter(host=host).exclude(status='archived').order_by('-created_at')

    context = {
        "host": host,
        "is_host_active": is_host_active,
        "last_connection_timestamp": last_connection_timestamp,
        "last_connection_display": last_connection_display,
        "user_is_admin": user_is_admin,
        "user_is_roboticien": user_is_roboticien,
        "service_tasks": service_tasks,
    }
    return render(request, "host_detail.html", context)


def get_github_commits(repo_owner, repo_name, count=2):
    """Récupère les derniers commits d'un dépôt GitHub"""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"

    response = requests.get(url, params={'per_page': count})

    if response.status_code == 200:
        commits = response.json()
        formatted_commits = []

        for commit in commits:
            author = commit['commit']['author']['name']
            message = commit['commit']['message']

            if len(message) > 100:
                message = message[:97] + "..."

            date_str = commit['commit']['author']['date']
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")

            priority = 'low'
            if 'fix' in message.lower() or 'bug' in message.lower():
                priority = 'medium'
            if 'urgent' in message.lower() or 'critical' in message.lower():
                priority = 'high'

            formatted_commits.append({
                'title': f"Mise à jour par {author}",
                'content': message,
                'date': date,
                'priority': priority,
                'url': commit['html_url']
            })

        return formatted_commits

    return []

@login_required
@role_required(['Admin', 'Roboticien'])
def sav_list_view(request):
    """Vue pour afficher la liste des tâches SAV"""
    # Exclure les tâches avec le statut 'archived'
    all_tasks = ServiceTask.objects.exclude(status='archived').order_by('-created_at')
    user_is_admin = request.user.roles.filter(name='Admin').exists()
    user_is_roboticien = request.user.roles.filter(name='Roboticien').exists()

    # Ordre de priorité personnalisé (du plus urgent au moins urgent)
    priority_order = Case(
        When(priority='urgent', then=Value(1)),
        When(priority='high', then=Value(2)),
        When(priority='medium', then=Value(3)),
        When(priority='low', then=Value(4)),
        default=Value(5),
        output_field=IntegerField(),
    )

    # Séparer les tâches par statut et les trier par priorité
    pending_tasks = all_tasks.filter(status='pending').annotate(
        priority_order=priority_order
    ).order_by('priority_order', '-created_at')

    in_progress_tasks = all_tasks.filter(status='in_progress').annotate(
        priority_order=priority_order
    ).order_by('priority_order', '-created_at')

    completed_tasks = all_tasks.filter(status='completed').order_by('-updated_at')

    return render(request, 'sav_list.html', {
        'tasks': all_tasks,  # Garder pour compatibilité
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'user_is_admin': user_is_admin,
        'user_is_roboticien': user_is_roboticien
    })

@login_required
@role_required(['Admin'])
def archive_completed_tasks(request):
    """Vue pour archiver toutes les tâches terminées"""
    if request.method == 'POST':
        # Changer le statut des tâches terminées en 'archived'
        completed_tasks = ServiceTask.objects.filter(status='completed')
        count = completed_tasks.count()
        completed_tasks.update(status='archived')

        messages.success(request, f"{count} tâches ont été archivées avec succès.")

    return redirect('sav_list')

from django.http import JsonResponse

@login_required
@role_required(['Admin', 'Roboticien'])
def sav_detail_view(request, task_id):
    """Vue pour afficher les détails d'une tâche SAV"""
    task = get_object_or_404(ServiceTask, id=task_id)
    user_is_admin = request.user.roles.filter(name='Admin').exists()
    user_is_roboticien = request.user.roles.filter(name='Roboticien').exists()

    if request.method == 'POST':
        # Mise à jour du statut via le formulaire standard
        if 'update_status' in request.POST:
            task.status = request.POST.get('status')
            task.save()
            messages.success(request, "Statut de la tâche mis à jour avec succès.")
            return redirect('sav_detail', task_id=task.id)
        
        # Mise à jour du titre ou de la description via AJAX
        elif 'update_field' in request.POST:
            field = request.POST.get('update_field')
            
            if field == 'title':
                new_title = request.POST.get('title')
                if new_title:
                    task.title = new_title
                    task.save()
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({'success': False, 'error': 'Le titre ne peut pas être vide'})
            
            elif field == 'description':
                new_description = request.POST.get('description')
                task.description = new_description
                task.save()
                return JsonResponse({'success': True})
            
            return JsonResponse({'success': False, 'error': 'Champ non reconnu'})

    return render(request, 'sav_detail.html', {
        'task': task,
        'user_is_admin': user_is_admin,
        'user_is_roboticien': user_is_roboticien
    })

@login_required
@role_required(['Admin', 'Roboticien'])
def add_service_task(request, host):
    """Vue pour ajouter une tâche SAV"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority')
        status = request.POST.get('status', 'pending')  # Ajout de cette ligne

        if title and description:
            ServiceTask.objects.create(
                host=host,
                title=title,
                description=description,
                priority=priority,
                status=status  # Ajout de cette ligne
            )
            messages.success(request, "Tâche SAV ajoutée avec succès.")
            return redirect('host_detail', host=host)
        else:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")

    return redirect('host_detail', host=host)



@login_required
def add_sav_task_view(request, host):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority')
        status = request.POST.get('status', 'pending')  # Valeur par défaut: 'pending'

        if title and description and priority:
            task = ServiceTask(
                host=host,
                title=title,
                description=description,
                priority=priority,
                status=status
            )
            task.save()

            # Rediriger vers la page de détail de l'hôte
            return redirect('host_detail', host=host)

    # En cas d'erreur ou si la méthode n'est pas POST, rediriger vers la page de détail de l'hôte
    return redirect('host_detail', host=host)