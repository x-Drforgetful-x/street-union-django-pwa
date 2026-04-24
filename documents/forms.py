from django import forms
from django.forms import inlineformset_factory

from company.models import CompanyProfile

from .models import Document, DocumentItem


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'document_type', 'number', 'client', 'issue_date', 'due_date', 'status',
            'reference', 'vat_mode', 'vat_rate', 'notes', 'terms'
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'terms': forms.Textarea(attrs={'rows': 3}),
            'number': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = CompanyProfile.objects.order_by('-updated_at').first()
        if company and not self.instance.pk:
            self.fields['vat_mode'].initial = company.default_vat_mode
            self.fields['vat_rate'].initial = company.default_vat_rate
            self.fields['terms'].initial = company.payment_terms
        if not self.instance.pk:
            doc_type = self.data.get('document_type') or self.initial.get('document_type') or self.fields['document_type'].initial or Document.DocumentType.QUOTE
            self.fields['number'].initial = Document.generate_next_number(doc_type)
        self.fields['number'].required = False
        self.fields['number'].disabled = True

    def clean_number(self):
        if self.instance.pk:
            return self.instance.number
        document_type = self.cleaned_data.get('document_type') or self.data.get('document_type') or Document.DocumentType.QUOTE
        return Document.generate_next_number(document_type)


DocumentItemFormSet = inlineformset_factory(
    Document,
    DocumentItem,
    fields=['description', 'quantity', 'unit_price', 'discount', 'is_vatable'],
    extra=3,
    can_delete=True,
)
