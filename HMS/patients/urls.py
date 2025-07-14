# filepath: /workspaces/codespaces-blank/HMS/patients/urls.py
from django.urls import path
from . import views
from  .views import request_labaratory_test

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
    path("re_admit/<int:id>/", views.re_admit, name="re_admit"),
    path("billing/<int:id>/", views.billing, name="billing"),
    path('update_payment/<int:bill_id>/', views.update_payment, name='update_payment'),
    path("patient_history/<int:id>/", views.patient_history, name="patient_history"),
    path("edit_patient_history/<int:history_id>/", views.edit_patient_history, name="edit_patient_history"),
    path('schedule/', views.schedule_appointment, name='schedule_appointment'),
    path('schedule/<int:patient_id>/', views.schedule_appointment, name='schedule_patient'),
    path('appointments/', views.view_appointments, name='view_appointments'),
    path('appointment/update/<int:appointment_id>/', views.update_appointment_status, name='update_appointment'),
    path('view_patient_ultrasound/<int:patient_id>/', views.view_patient_ultrasounds, name='view_patient_ultrasounds'),
    path('request_ultrasound/<int:patient_id>',views.request_ultrasound,name='request_ultrasound'),
    path('request_lab_test/<int:patient_id>/', views.request_lab_test, name='request_lab_test'),
    path('view_patient_lab_results/<int:patient_id>/', views.view_patient_lab_results, name='view_patient_lab_results'),
    path('request_labaratory_test/<int:patient_id>/', request_labaratory_test, name='request_labaratory_test'),
    path('download_receipt/<int:bill_id>/', views.download_receipt, name='download_receipt'),
    path('discharge/<int:patient_id>/', views.discharge_patient, name='patient_discharge'),
    path('discharge/summary/<int:patient_id>/pdf/', views.generate_discharge_summary_pdf, name='generate_discharge_summary_pdf'),

    

]
