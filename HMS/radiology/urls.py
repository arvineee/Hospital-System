from .views import (
    ultrasound_list,
    ultrasound_create,
    ultrasound_update,
)
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', ultrasound_list, name='ultrasound_list'),
    path('create/', ultrasound_create, name='ultrasound_create'),
    path('update/<int:ultrasound_id>/', ultrasound_update, name='ultrasound_update'),
]