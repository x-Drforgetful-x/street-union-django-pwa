from django.contrib import admin
from .models import Document, DocumentItem


class DocumentItemInline(admin.TabularInline):
    model = DocumentItem
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('number', 'document_type', 'client', 'status', 'total_amount', 'vat_mode', 'updated_at')
    list_filter = ('document_type', 'status', 'vat_mode')
    search_fields = ('number', 'client__client_name', 'client__company_name')
    inlines = [DocumentItemInline]
