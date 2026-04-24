from decimal import Decimal, InvalidOperation

from django import template
from company.models import CompanyProfile

register = template.Library()


def _to_decimal(value):
    if value in (None, ''):
        return Decimal('0.00')
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.00')


@register.filter(name="money")
def money(value):
    amount = _to_decimal(value).quantize(Decimal('0.01'))
    company = CompanyProfile.objects.order_by('-updated_at').first()
    symbol = company.currency_symbol if company else 'R'
    return f"{symbol} {amount:,.2f}"


@register.filter(name="qty")
def qty(value):
    amount = _to_decimal(value)
    if amount == amount.to_integral():
        return f"{amount.to_integral():,}"
    return f"{amount:,.2f}"


@register.filter(name="percent_clean")
def percent_clean(value):
    amount = _to_decimal(value)
    if amount == amount.to_integral():
        return f"{amount.to_integral()}%"
    return f"{amount.quantize(Decimal('0.01'))}%"
