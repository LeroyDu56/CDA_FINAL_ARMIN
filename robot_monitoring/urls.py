from django.contrib import admin
from django.urls import path
from auth_app import views

urlpatterns = [
    # 1) Votre route perso
    path('admin/roles/', views.admin_roles_view, name='admin_roles'),

    # 2) Puis la route vers le Django Admin
    path('admin/', admin.site.urls),

    # 3) Les autres routes
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('robots/', views.robot_list_view, name='robot_list'),
    path('host/<str:host>/', views.host_detail_view, name='host_detail'),
]
