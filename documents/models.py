from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from clients.models import Client
from company.models import CompanyProfile


def get_company_profile():
    return CompanyProfile.objects.order_by('-updated_at').first()


def get_currency_symbol(currency_code='ZAR'):
    return {
        'ZAR': 'R',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'AUD': 'A$',
        'CAD': 'C$',
        'NZD': 'NZ$',
        'JPY': '¥',
        'CNY': '¥',
        'INR': '₹',
        'AED': 'د.إ',
        'SAR': '﷼',
        'KES': 'KSh',
        'NGN': '₦',
        'BWP': 'P',
        'NAD': 'N$',
    }.get(currency_code, 'R')


def format_currency(value, currency_code='ZAR'):
    amount = Decimal(value or 0).quantize(Decimal('0.01'))
    return f"{get_currency_symbol(currency_code)} {amount:,.2f}"


def format_quantity(value):
    amount = Decimal(value or 0)
    if amount == amount.to_integral():
        return f"{int(amount):,}"
    return f"{amount.quantize(Decimal('0.01'))}"


def format_percent(value):
    amount = Decimal(value or 0)
    if amount == amount.to_integral():
        return f"{int(amount)}%"
    return f"{amount.quantize(Decimal('0.01'))}%"


class Document(models.Model):
    class DocumentType(models.TextChoices):
        QUOTE = 'quote', 'Quote'
        INVOICE = 'invoice', 'Invoice'
        SALES_ORDER = 'sales_order', 'Sales Order'

    class VatMode(models.TextChoices):
        EXCLUSIVE = 'exclusive', 'VAT Exclusive'
        INCLUSIVE = 'inclusive', 'VAT Inclusive'
        NONE = 'none', 'No VAT'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        UNPAID = 'unpaid', 'Unpaid'
        PARTIAL = 'partial', 'Partial'
        PAID = 'paid', 'Paid'

    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    number = models.CharField(max_length=50, unique=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    issue_date = models.DateField()
    due_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    reference = models.CharField(max_length=255, blank=True)
    vat_mode = models.CharField(max_length=20, choices=VatMode.choices, default=VatMode.EXCLUSIVE)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('15.00'))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='pdfs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.get_document_type_display()} {self.number}'

    @classmethod
    def generate_next_number(cls, document_type):
        company = get_company_profile()
        prefix_map = {
            cls.DocumentType.QUOTE: company.quote_prefix if company and company.quote_prefix else 'QUO',
            cls.DocumentType.INVOICE: company.invoice_prefix if company and company.invoice_prefix else 'INV',
            cls.DocumentType.SALES_ORDER: company.sales_order_prefix if company and company.sales_order_prefix else 'SO',
        }
        prefix = prefix_map.get(document_type, 'DOC')

        last_document = cls.objects.filter(document_type=document_type).order_by('-id').first()
        next_index = 1
        if last_document and last_document.number:
            try:
                next_index = int(last_document.number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                next_index = last_document.id + 1
        return f'{prefix}-{next_index:05d}'

    def save(self, *args, **kwargs):
        if self._state.adding or not self.number:
            self.number = self.generate_next_number(self.document_type)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pdf_file:
            self.pdf_file.delete(save=False)
        super().delete(*args, **kwargs)

    def calculate_totals(self):
        subtotal_raw = Decimal('0.00')
        taxable_raw = Decimal('0.00')
        for item in self.items.all():
            line_total = item.line_total
            subtotal_raw += line_total
            if item.is_vatable:
                taxable_raw += line_total

        vat_amount = Decimal('0.00')
        subtotal = subtotal_raw
        total = subtotal_raw

        if self.vat_mode == self.VatMode.EXCLUSIVE:
            vat_amount = taxable_raw * (self.vat_rate / Decimal('100.00'))
            total = subtotal_raw + vat_amount
        elif self.vat_mode == self.VatMode.INCLUSIVE:
            if self.vat_rate > 0:
                vat_amount = taxable_raw * (self.vat_rate / (Decimal('100.00') + self.vat_rate))
            subtotal = subtotal_raw - vat_amount
            total = subtotal_raw

        self.subtotal = subtotal.quantize(Decimal('0.01'))
        self.vat_amount = vat_amount.quantize(Decimal('0.01'))
        self.total_amount = total.quantize(Decimal('0.01'))

    def generate_pdf(self):
        company = get_company_profile()
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        left = 16 * mm
        right = width - (16 * mm)
        top_margin = 16 * mm
        bottom_margin = 16 * mm
        y = height - top_margin

        def wrap_text(text_value, max_width, font_name="Helvetica", font_size=9):
            words = str(text_value or '').split()
            if not words:
                return ['']
            lines = []
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if stringWidth(candidate, font_name, font_size) <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            return lines

        def ensure_space(required_height):
            nonlocal y
            if y - required_height < bottom_margin:
                pdf.showPage()
                y = height - top_margin
                draw_page_header(minimal=True)

        def draw_wrapped_block(label, text_value, x, width_available, label_size=11, text_size=9, gap_after=4 * mm):
            nonlocal y
            if not text_value:
                return
            label_height = 6 * mm
            raw_lines = []
            for paragraph in str(text_value).splitlines() or ['']:
                raw_lines.extend(wrap_text(paragraph, width_available, "Helvetica", text_size))
                if paragraph == '':
                    raw_lines.append('')
            line_height = 4.8 * mm
            needed = label_height + max(line_height, len(raw_lines) * line_height) + gap_after
            ensure_space(needed)
            pdf.setFont('Helvetica-Bold', label_size)
            pdf.setFillColor(colors.HexColor('#111111'))
            pdf.drawString(x, y, label)
            y -= label_height
            pdf.setFont('Helvetica', text_size)
            pdf.setFillColor(colors.HexColor('#374151'))
            for row in raw_lines:
                ensure_space(line_height + gap_after)
                pdf.drawString(x, y, row)
                y -= line_height
            y -= gap_after

        def draw_page_header(minimal=False):
            nonlocal y
            pdf.setFillColor(colors.HexColor('#111111'))
            pdf.rect(0, height - 30 * mm, width, 30 * mm, fill=1, stroke=0)
            pdf.setFillColor(colors.HexColor('#D4A437'))
            pdf.rect(0, height - 33 * mm, width, 3 * mm, fill=1, stroke=0)

            if company and company.logo:
                try:
                    logo = ImageReader(company.logo.path)
                    pdf.drawImage(logo, left, height - 25 * mm, width=28 * mm, height=17 * mm, preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass

            pdf.setFillColor(colors.white)
            pdf.setFont('Helvetica-Bold', 16 if not minimal else 14)
            pdf.drawString(50 * mm, height - 14 * mm, company.company_name if company else 'Your Company Name')
            pdf.setFont('Helvetica', 8.5)
            subtitle = company.email if company and company.email else 'Add company details in settings'
            pdf.drawString(50 * mm, height - 20 * mm, subtitle)
            if company and company.phone:
                pdf.drawString(50 * mm, height - 25 * mm, company.phone)
            y = height - (40 * mm if not minimal else 38 * mm)

        draw_page_header()

        title_map = {
            self.DocumentType.QUOTE: 'QUOTE',
            self.DocumentType.INVOICE: 'INVOICE',
            self.DocumentType.SALES_ORDER: 'SALES ORDER',
        }
        title = title_map.get(self.document_type, 'DOCUMENT')

        pdf.setFillColor(colors.HexColor('#111111'))
        pdf.roundRect(left, y - 16 * mm, 78 * mm, 18 * mm, 4 * mm, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawString(left + 4 * mm, y - 6 * mm, title)
        pdf.setFont('Helvetica-Bold', 11)
        pdf.setFillColor(colors.HexColor('#D4A437'))
        pdf.drawString(left + 4 * mm, y - 12 * mm, self.number)

        info_x = 102 * mm
        pdf.setFillColor(colors.HexColor('#111111'))
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(info_x, y - 2 * mm, 'Document Details')
        pdf.setFont('Helvetica', 8.8)
        info_rows = [
            f'Issue date: {self.issue_date}',
            f'{"Expiry date" if self.document_type == self.DocumentType.QUOTE else "Due date"}: {self.due_date}' if self.due_date else None,
            f'Reference: {self.reference}' if self.reference else None,
            f'Status: {self.get_status_display()}',
        ]
        info_y = y - 7 * mm
        for row in [r for r in info_rows if r]:
            pdf.drawString(info_x, info_y, row)
            info_y -= 4.6 * mm
        y -= 24 * mm

        left_col_w = 88 * mm
        right_col_x = 110 * mm
        right_col_w = right - right_col_x

        pdf.setFillColor(colors.HexColor('#FFF8E6'))
        pdf.roundRect(left, y - 28 * mm, left_col_w, 30 * mm, 4 * mm, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor('#111111'))
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(left + 4 * mm, y - 5 * mm, 'Bill To')
        pdf.setFont('Helvetica', 8.8)
        client_lines = [self.client.client_name]
        if self.client.company_name:
            client_lines.append(self.client.company_name)
        if self.client.address:
            client_lines.extend(self.client.address.splitlines())
        if self.client.email or self.client.phone:
            client_lines.append(' | '.join([v for v in [self.client.email, self.client.phone] if v]))
        client_y = y - 10 * mm
        for row in client_lines[:5]:
            pdf.drawString(left + 4 * mm, client_y, str(row))
            client_y -= 4.5 * mm

        pdf.setFillColor(colors.HexColor('#F8FAFC'))
        pdf.roundRect(right_col_x, y - 28 * mm, right_col_w, 30 * mm, 4 * mm, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor('#111111'))
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(right_col_x + 4 * mm, y - 5 * mm, 'Company Information')
        pdf.setFont('Helvetica', 8.6)
        details = []
        if company:
            if company.address:
                details.extend(company.address.splitlines())
            if company.vat_registered and company.vat_number:
                details.append(f'VAT No: {company.vat_number}')
            if company.bank_name:
                details.append(f'Bank: {company.bank_name}')
            if company.account_number:
                details.append(f'Account No: {company.account_number}')
        company_y = y - 10 * mm
        for row in details[:5]:
            pdf.drawString(right_col_x + 4 * mm, company_y, str(row))
            company_y -= 4.5 * mm

        y -= 36 * mm

        def draw_table_header():
            nonlocal y
            headers = ['Description', 'Qty', 'Unit Price', 'VAT', 'Line Total']
            col_x = [left, 100 * mm, 124 * mm, 150 * mm, 171 * mm]
            pdf.setFillColor(colors.HexColor('#111111'))
            pdf.roundRect(left, y - 7 * mm, right - left, 9 * mm, 2 * mm, fill=1, stroke=0)
            pdf.setFillColor(colors.white)
            pdf.setFont('Helvetica-Bold', 8.5)
            for hx, header in zip(col_x, headers):
                pdf.drawString(hx + 1.5 * mm, y - 4 * mm, header)
            y -= 11 * mm
            return col_x

        col_x = draw_table_header()
        pdf.setFont('Helvetica', 8.6)
        pdf.setFillColor(colors.HexColor('#111111'))

        for item in self.items.all():
            desc_lines = wrap_text(item.description, 78 * mm, 'Helvetica', 8.6)
            row_height = max(6 * mm, len(desc_lines) * 4.4 * mm)
            ensure_space(row_height + 4 * mm)
            if y > bottom_margin and y < 45 * mm:
                pdf.showPage()
                y = height - top_margin
                draw_page_header(minimal=True)
                col_x = draw_table_header()
            pdf.setStrokeColor(colors.HexColor('#E5E7EB'))
            pdf.line(left, y - 1.8 * mm, right, y - 1.8 * mm)
            text_y = y
            for line_value in desc_lines:
                pdf.drawString(col_x[0] + 1.5 * mm, text_y, line_value)
                text_y -= 4.4 * mm
            vat_label = format_percent(self.vat_rate) if item.is_vatable and self.vat_mode != self.VatMode.NONE else '0%'
            pdf.drawRightString(col_x[1] + 18 * mm, y, format_quantity(item.quantity))
            pdf.drawRightString(col_x[2] + 22 * mm, y, format_currency(item.unit_price))
            pdf.drawRightString(col_x[3] + 18 * mm, y, vat_label)
            pdf.drawRightString(right - 2 * mm, y, format_currency(item.line_total))
            y -= row_height

        y -= 3 * mm
        ensure_space(42 * mm)
        box_x = 116 * mm
        box_w = right - box_x
        pdf.setFillColor(colors.HexColor('#FFF8E6'))
        pdf.setStrokeColor(colors.HexColor('#D4A437'))
        pdf.roundRect(box_x, y - 25 * mm, box_w, 28 * mm, 4 * mm, stroke=1, fill=1)
        pdf.setFont('Helvetica', 10)
        pdf.setFillColor(colors.HexColor('#111111'))
        pdf.drawString(box_x + 4 * mm, y - 6 * mm, 'Subtotal')
        pdf.drawRightString(right - 4 * mm, y - 6 * mm, format_currency(self.subtotal, company.currency if company else 'ZAR'))
        pdf.drawString(box_x + 4 * mm, y - 13 * mm, 'VAT')
        pdf.drawRightString(right - 4 * mm, y - 13 * mm, format_currency(self.vat_amount, company.currency if company else 'ZAR'))
        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(box_x + 4 * mm, y - 21 * mm, 'Total')
        pdf.drawRightString(right - 4 * mm, y - 21 * mm, format_currency(self.total_amount, company.currency if company else 'ZAR'))
        y -= 32 * mm

        draw_wrapped_block('Notes', self.notes, left, right - left)
        draw_wrapped_block('Terms', self.terms, left, right - left)
        if company and company.footer_note:
            draw_wrapped_block('Footer Note', company.footer_note, left, right - left, label_size=10, text_size=8.5, gap_after=2 * mm)

        pdf.save()
        buffer.seek(0)
        filename = f'{self.number}.pdf'
        self.pdf_file.save(filename, ContentFile(buffer.read()), save=False)
        buffer.close()



class DocumentItem(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_vatable = models.BooleanField(default=True)

    @property
    def line_total(self):
        return (self.quantity * self.unit_price) - self.discount

    def __str__(self):
        return self.description
