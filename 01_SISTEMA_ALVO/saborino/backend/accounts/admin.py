from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Socio

User = get_user_model()

admin.site.register(User, UserAdmin)


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'usuario', 'ativo')
