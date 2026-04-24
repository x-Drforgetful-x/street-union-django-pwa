from django.contrib import admin
from .models import CompanyProfile


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'vat_registered', 'default_vat_rate', 'default_vat_mode', 'updated_at')
