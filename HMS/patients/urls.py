# filepath: /workspaces/codespaces-blank/HMS/patients/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.all_patients, name='all_patients'),  # Map the all_patients view
    path('register/', views.pat_register, name='pat_register'),
    path('search/', views.pat_search, name='pat_search'),
    path('search/<str:name>/', views.pat_search, name='pat_search_with_name'), 
    path('update/<int:id>/', views.pat_update, name='pat_update'),
    path('delete/<int:id>/', views.pat_delete, name='pat_delete'),
    path('view/<int:id>/', views.pat_view, name='pat_view'),
    path('prescribe_drugs/<int:id>/', views.prescribe_drugs, name='prescribe_drugs'),
    path("drug_issued/<int:id>/", views.drug_issued, name="drug_issued"),
    path("drug_issued/", views.drug_issued, name="drug_issued"),  
    path("patient_discharge/<int:id>/", views.patient_discharge, name="patient_discharge"),
    path("re_admit/<int:id>/", views.re_admit, name="re_admit"),
    path("billing/<int:id>/", views.billing, name="billing"),
    path("patient_history/<int:id>/", views.patient_history, name="patient_history"),
    path('schedule/', views.schedule_appointment, name='schedule_appointment'),
    path('schedule/<int:patient_id>/', views.schedule_appointment, name='schedule_patient'),
    path('appointments/', views.view_appointments, name='view_appointments'),
    path('appointment/update/<int:appointment_id>/', views.update_appointment_status, name='update_appointment'),

]
