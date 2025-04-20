from django.urls import path
from . import views

urlpatterns = [
    path('register/',views.pat_register, name="pat_register"), # url to register patients
    path('',views.home, name="home"), # url to view all patients
]