from django.urls import path

from . import views
from patients.views import analytics_dashboard
from .views import (
    drug_list_and_alerts 
)

urlpatterns = [
    path('drugs/', views.all_drugs, name='all_drugs'),
    path('drugs/add_drug/', views.add_drug, name='add_drug'),
    path('drugs/update/<int:id>/', views.drug_update, name='drug_update'),
    path('drugs/delete/<int:id>/', views.drug_delete, name='drug_delete'),
    path('drugs/search/', views.drug_search, name='drug_search'),
    path('drugs/issue/', views.drug_issue, name='drug_issue'),
    path('drugs/issue/<int:patient_id>/', views.drug_issue, name='drug_issue'),
    path('pharmacy_dashboard/', views.pharmacy_dashboard, name='pharmacy_dashboard'),

    # OTC sales
    path('pharmacy/otc_sale/', views.otc_sale, name='otc_sale'),
    path('pharmacy/otc_sales_list/', views.otc_sales_list, name='otc_sales_list'),
    # Analytics Dashboard
    path('analytics/dashboard/', analytics_dashboard, name='analytics_dashboard'),
    path('patients/<int:patient_id>/prescriptions/create/', views.create_prescription, name='create_prescription'),
    path('patients/<int:patient_id>/prescriptions/', views.patient_prescriptions, name='patient_prescriptions'),
    path('prescriptions/<int:prescription_id>/', views.prescription_detail, name='prescription_detail'),

    # New URLs for Supplier Management
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),

    # New URL for Inventory Reconciliation
    path('pharmacy/reconciliation/', views.inventory_reconciliation, name='inventory_reconciliation'),
    path('api/stock_warnings/', views.get_stock_warnings, name='api_stock_warnings'),
    path('drugs/alerts/', drug_list_and_alerts, name='drug_list_and_alerts'),
  
]