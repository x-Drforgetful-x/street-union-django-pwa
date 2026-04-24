from django.urls import path
from .views import ConvertQuoteToInvoiceView, DocumentCreateView, DocumentDeleteView, DocumentDetailView, DocumentListView, DocumentUpdateView, NextDocumentNumberView

urlpatterns = [
    path('next-number/', NextDocumentNumberView.as_view(), name='document-next-number'),
    path('', DocumentListView.as_view(), name='document-list'),
    path('new/', DocumentCreateView.as_view(), name='document-create'),
    path('<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('<int:pk>/edit/', DocumentUpdateView.as_view(), name='document-update'),
    path('<int:pk>/delete/', DocumentDeleteView.as_view(), name='document-delete'),
    path('<int:pk>/convert-to-invoice/', ConvertQuoteToInvoiceView.as_view(), name='document-convert-to-invoice'),
]
