from decimal import Decimal
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.views.generic import TemplateView

from clients.models import Client
from company.models import CompanyProfile
from documents.models import Document


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        documents = Document.objects.select_related('client')
        quotes = documents.filter(document_type=Document.DocumentType.QUOTE)
        invoices = documents.filter(document_type=Document.DocumentType.INVOICE)
        sales_orders = documents.filter(document_type=Document.DocumentType.SALES_ORDER)

        open_quote_statuses = [
            Document.Status.DRAFT,
            Document.Status.SENT,
            Document.Status.APPROVED,
        ]

        unpaid_invoice_statuses = [
            Document.Status.UNPAID,
            Document.Status.PARTIAL,
        ]

        def money_sum(queryset):
            return queryset.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        context['company'] = CompanyProfile.objects.order_by('-updated_at').first()
        context['client_count'] = Client.objects.count()
        context['recent_documents'] = documents.order_by('-created_at')[:8]

        context['quote_count'] = quotes.count()
        context['invoice_count'] = invoices.count()
        context['sales_order_count'] = sales_orders.count()

        context['quote_total_amount'] = money_sum(quotes)
        context['invoice_total_amount'] = money_sum(invoices)
        context['sales_order_amount'] = money_sum(sales_orders)

        context['open_quotes'] = quotes.filter(status__in=open_quote_statuses).count()
        context['open_quote_amount'] = money_sum(quotes.filter(status__in=open_quote_statuses))

        context['unpaid_invoices'] = invoices.filter(status__in=unpaid_invoice_statuses).count()
        context['outstanding_amount'] = money_sum(invoices.filter(status__in=unpaid_invoice_statuses))

        context['paid_amount'] = money_sum(invoices.filter(status=Document.Status.PAID))
        context['partial_amount'] = money_sum(invoices.filter(status=Document.Status.PARTIAL))
        context['unpaid_amount'] = money_sum(invoices.filter(status=Document.Status.UNPAID))

        monthly_data = []
        monthly_qs = (
            documents
            .annotate(month=TruncMonth('issue_date'))
            .values('month', 'document_type')
            .annotate(total=Sum('total_amount'))
            .order_by('month')
        )
        grouped = {}
        for row in monthly_qs:
            if not row['month']:
                continue
            label = row['month'].strftime('%b %Y')
            bucket = grouped.setdefault(label, {'quote': 0.0, 'invoice': 0.0, 'sales_order': 0.0})
            bucket[row['document_type']] = float(row['total'] or 0)
        for label, values in list(grouped.items())[-6:]:
            monthly_data.append({'label': label, **values})
        context['chart_data_json'] = json.dumps(monthly_data)
        return context
