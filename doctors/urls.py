from django.urls import path

from . import views

app_name = 'doctors'

urlpatterns = [
    path('', views.doctor_list, name='list'),
    path('add/', views.doctor_create, name='create'),
    path('<uuid:pk>/edit/', views.doctor_edit, name='edit'),
]