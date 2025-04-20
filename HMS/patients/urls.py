from django.urls import path
from . import views

urlpatterns = [
    path('',views.pat_register, name="pat_register"), # url to register patients
]