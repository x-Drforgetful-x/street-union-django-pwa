from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'company_name', 'email', 'phone', 'created_at')
    search_fields = ('client_name', 'company_name', 'email')
