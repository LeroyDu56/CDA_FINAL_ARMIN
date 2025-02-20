from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AuthLog, Permission, Role, Grant, IsAssignedTo

# Inline pour gérer la relation User <-> Role via IsAssignedTo
class IsAssignedToInline(admin.TabularInline):
    model = IsAssignedTo
    extra = 1  # Nombre de lignes "vides" proposées par défaut

class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    ordering = ('email',)
    
    # On ne met pas 'roles' dans fieldsets
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Dates', {'fields': ('last_login', 'created_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
        ),
    )
    
    # On ajoute notre inline pour gérer l’assignation des rôles
    inlines = [IsAssignedToInline]

admin.site.register(User, UserAdmin)
admin.site.register(AuthLog)
admin.site.register(Permission)
admin.site.register(Role)
admin.site.register(Grant)
admin.site.register(IsAssignedTo)
