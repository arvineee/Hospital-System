from django.urls import path
from . import views

urlpatterns = [
    path('drugs/', views.all_drugs, name='all_drugs'),
    path('drugs/add_drug/', views.add_drug, name='add_drug'),
    path('drugs/update/<int:id>/', views.drug_update, name='drug_update'),
    path('drugs/delete/<int:id>/', views.drug_delete, name='drug_delete'),
    path('drugs/search/', views.drug_search, name='drug_search'),
    path('drugs/issue/', views.drug_issue, name='drug_issue'),
    path('drugs/issue/<int:id>/', views.drug_issue, name='drug_issue'),
]