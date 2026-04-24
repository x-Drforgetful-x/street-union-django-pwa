from django.db import models


class CompanyProfile(models.Model):
    class VatMode(models.TextChoices):
        EXCLUSIVE = 'exclusive', 'VAT Exclusive'
        INCLUSIVE = 'inclusive', 'VAT Inclusive'
        NONE = 'none', 'No VAT'



    class Currency(models.TextChoices):
        ZAR = 'ZAR', 'South African Rand (R)'
        USD = 'USD', 'US Dollar ($)'
        EUR = 'EUR', 'Euro (€)'
        GBP = 'GBP', 'British Pound (£)'
        AUD = 'AUD', 'Australian Dollar (A$)'
        CAD = 'CAD', 'Canadian Dollar (C$)'
        NZD = 'NZD', 'New Zealand Dollar (NZ$)'
        JPY = 'JPY', 'Japanese Yen (¥)'
        CNY = 'CNY', 'Chinese Yuan (¥)'
        INR = 'INR', 'Indian Rupee (₹)'
        AED = 'AED', 'UAE Dirham (د.إ)'
        SAR = 'SAR', 'Saudi Riyal (﷼)'
        KES = 'KES', 'Kenyan Shilling (KSh)'
        NGN = 'NGN', 'Nigerian Naira (₦)'
        BWP = 'BWP', 'Botswana Pula (P)'
        NAD = 'NAD', 'Namibian Dollar (N$)'

    company_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    vat_registered = models.BooleanField(default=True)
    currency = models.CharField(max_length=10, choices=Currency.choices, default=Currency.ZAR)
    vat_number = models.CharField(max_length=100, blank=True)
    default_vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=15)
    default_vat_mode = models.CharField(max_length=20, choices=VatMode.choices, default=VatMode.EXCLUSIVE)
    bank_name = models.CharField(max_length=100, blank=True)
    account_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=100, blank=True)
    branch_code = models.CharField(max_length=100, blank=True)
    quote_prefix = models.CharField(max_length=20, default='QUO')
    invoice_prefix = models.CharField(max_length=20, default='INV')
    sales_order_prefix = models.CharField(max_length=20, default='SO')
    payment_terms = models.TextField(blank=True)
    footer_note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

    @property
    def currency_symbol(self):
        return {
            self.Currency.ZAR: 'R',
            self.Currency.USD: '$',
            self.Currency.EUR: '€',
            self.Currency.GBP: '£',
            self.Currency.AUD: 'A$',
            self.Currency.CAD: 'C$',
            self.Currency.NZD: 'NZ$',
            self.Currency.JPY: '¥',
            self.Currency.CNY: '¥',
            self.Currency.INR: '₹',
            self.Currency.AED: 'د.إ',
            self.Currency.SAR: '﷼',
            self.Currency.KES: 'KSh',
            self.Currency.NGN: '₦',
            self.Currency.BWP: 'P',
            self.Currency.NAD: 'N$',
        }.get(self.currency, 'R')
