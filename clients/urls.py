from django.urls import path
from .views import ClientCreateView, ClientListView, ClientUpdateView

urlpatterns = [
    path('', ClientListView.as_view(), name='client-list'),
    path('new/', ClientCreateView.as_view(), name='client-create'),
    path('<int:pk>/edit/', ClientUpdateView.as_view(), name='client-update'),
]
