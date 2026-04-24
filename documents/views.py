from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import DocumentForm, DocumentItemFormSet
from .models import Document, DocumentItem


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20

    def get_queryset(self):
        queryset = Document.objects.select_related('client').order_by('-created_at')
        selected_type = self.request.GET.get('type')
        selected_status = self.request.GET.get('status')
        query = self.request.GET.get('q')

        if selected_type in {choice[0] for choice in Document.DocumentType.choices}:
            queryset = queryset.filter(document_type=selected_type)
        if selected_status in {choice[0] for choice in Document.Status.choices}:
            queryset = queryset.filter(status=selected_status)
        if query:
            queryset = queryset.filter(
                Q(number__icontains=query)
                | Q(client__client_name__icontains=query)
                | Q(client__company_name__icontains=query)
                | Q(reference__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['type_choices'] = Document.DocumentType.choices
        context['status_choices'] = Document.Status.choices
        return context


class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = 'documents/document_detail.html'
    context_object_name = 'document'


class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'documents/document_form.html'
    success_url = reverse_lazy('document-list')

    def get_initial(self):
        initial = super().get_initial()
        selected_type = self.request.GET.get('type')
        if selected_type in {choice[0] for choice in Document.DocumentType.choices}:
            initial['document_type'] = selected_type
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = DocumentItemFormSet(self.request.POST)
        else:
            context['formset'] = DocumentItemFormSet()
        context['title'] = 'Create Document'
        context['next_numbers'] = {value: Document.generate_next_number(value) for value, _label in Document.DocumentType.choices}
        context['next_number_url'] = reverse('document-next-number')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            form.instance.number = Document.generate_next_number(form.cleaned_data['document_type'])
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            self.object.calculate_totals()
            self.object.generate_pdf()
            self.object.save(update_fields=['subtotal', 'vat_amount', 'total_amount', 'pdf_file', 'updated_at'])
            messages.success(self.request, f'{self.object.get_document_type_display()} {self.object.number} saved and PDF generated successfully.')
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)


class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = 'documents/document_form.html'
    success_url = reverse_lazy('document-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = DocumentItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = DocumentItemFormSet(instance=self.object)
        context['title'] = 'Update Document'
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            self.object.calculate_totals()
            self.object.generate_pdf()
            self.object.save()
            messages.success(self.request, 'Document updated and PDF regenerated successfully.')
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document
    template_name = 'documents/document_confirm_delete.html'
    context_object_name = 'document'
    success_url = reverse_lazy('document-list')

    def form_valid(self, form):
        document_label = f'{self.object.get_document_type_display()} {self.object.number}'
        messages.success(self.request, f'{document_label} was deleted successfully.')
        return super().form_valid(form)


class ConvertQuoteToInvoiceView(LoginRequiredMixin, View):
    def post(self, request, pk):
        quote = get_object_or_404(Document, pk=pk, document_type=Document.DocumentType.QUOTE)
        invoice = Document.objects.create(
            document_type=Document.DocumentType.INVOICE,
            client=quote.client,
            issue_date=quote.issue_date,
            due_date=quote.due_date,
            status=Document.Status.UNPAID,
            reference=quote.reference or f'Converted from {quote.number}',
            vat_mode=quote.vat_mode,
            vat_rate=quote.vat_rate,
            notes=quote.notes,
            terms=quote.terms,
        )
        for item in quote.items.all():
            DocumentItem.objects.create(
                document=invoice,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                is_vatable=item.is_vatable,
                discount=item.discount,
            )
        invoice.calculate_totals()
        invoice.generate_pdf()
        invoice.save()
        messages.success(request, f'Quote {quote.number} was converted to invoice {invoice.number}.')
        return redirect(reverse('document-detail', kwargs={'pk': invoice.pk}))


class NextDocumentNumberView(LoginRequiredMixin, View):
    def get(self, request):
        document_type = request.GET.get('type', Document.DocumentType.QUOTE)
        valid_types = {choice[0] for choice in Document.DocumentType.choices}
        if document_type not in valid_types:
            document_type = Document.DocumentType.QUOTE
        return JsonResponse({'document_type': document_type, 'number': Document.generate_next_number(document_type)})
