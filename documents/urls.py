# documents/urls.py
from django.urls import path

from . import views

app_name = 'documents'

urlpatterns = [
    path('visit/<uuid:visit_pk>/upload/', views.document_upload_to_visit, name='upload_visit'),
    path('patient/<uuid:patient_pk>/upload/', views.document_upload_administrative, name='upload_administrative'),
    path('<uuid:pk>/delete/', views.document_delete, name='delete'),
    path('visit/<uuid:visit_pk>/generate/cnss/', views.generate_cnss_pdf, name='generate_cnss'),
    path('visit/<uuid:visit_pk>/generate/custom/', views.generate_custom_pdf, name='generate_custom'),
    path('visit/<uuid:visit_pk>/cnss-form/', views.cnss_request_form_view, name='cnss_form'),
    path('visit/<uuid:visit_pk>/cnss-form/generate-sheet/', views.generate_filled_cnss_sheet, name='generate_cnss_sheet'),
    path('visit/<uuid:visit_pk>/cnss-form/preview/', views.cnss_form_preview, name='cnss_form_preview'),
]