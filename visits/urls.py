# visits/urls.py
from django.urls import path

from . import views

app_name = 'visits'

urlpatterns = [
    path('<uuid:pk>/', views.visit_detail, name='detail'),
    path('<uuid:pk>/edit/', views.visit_edit, name='edit'),
    path('<uuid:pk>/status/', views.visit_cancel, name='status'),
    path('patient/<uuid:patient_pk>/add/', views.visit_create, name='create'),
]