from django.urls import path

from .views import CompanyProfileUpdateView

urlpatterns = [
    path("settings/", CompanyProfileUpdateView.as_view(), name="company-settings"),
]
