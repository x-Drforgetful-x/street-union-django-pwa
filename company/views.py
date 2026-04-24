from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from .forms import CompanyProfileForm
from .models import CompanyProfile


class CompanyProfileUpdateView(LoginRequiredMixin, View):
    template_name = "company/company_form.html"

    def get_object(self):
        return CompanyProfile.objects.order_by("-updated_at").first()

    def get(self, request):
        company = self.get_object()
        form = CompanyProfileForm(instance=company)
        return render(request, self.template_name, {"form": form, "company": company})

    def post(self, request):
        company = self.get_object()
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            company = form.save()
            messages.success(request, "Company profile updated successfully.")
            return redirect("company-settings")
        return render(request, self.template_name, {"form": form, "company": company})
