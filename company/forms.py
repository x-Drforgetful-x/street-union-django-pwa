from django import forms

from .models import CompanyProfile


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = [
            "company_name", "logo", "email", "phone", "address",
            "vat_registered", "currency", "vat_number", "default_vat_rate", "default_vat_mode",
            "bank_name", "account_name", "account_number", "branch_code",
            "quote_prefix", "invoice_prefix", "sales_order_prefix",
            "payment_terms", "footer_note",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "payment_terms": forms.Textarea(attrs={"rows": 3}),
            "footer_note": forms.Textarea(attrs={"rows": 3}),
        }
