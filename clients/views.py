from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from .forms import ClientForm
from .models import Client


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    ordering = ['-created_at']


class ClientCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('client-list')
    success_message = 'Client created successfully.'


class ClientUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('client-list')
    success_message = 'Client updated successfully.'
