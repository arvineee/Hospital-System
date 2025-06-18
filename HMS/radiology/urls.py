from .views import (
    ultrasound_list,
    ultrasound_create,
    ultrasound_update,
    ultrasound_detail,
    ultrasound_delete,
    ultrasound_requests_list,
    add_ultrasound_for_request,
    reject_ultrasound_request,
)
from django.urls import path

urlpatterns = [
    path('', ultrasound_list, name='ultrasound_list'),
    path('create/', ultrasound_create, name='ultrasound_create'),
    path('update/<int:ultrasound_id>/', ultrasound_update, name='ultrasound_update'),
    path('detail/<int:ultrasound_id>/', ultrasound_detail, name='ultrasound_detail'),
    path('delete/<int:ultrasound_id>/', ultrasound_delete, name='ultrasound_delete'),
    path("request_list",ultrasound_requests_list, name='ultrasound_requests_list'),
    path('add_ultrasound_for_request/<int:request_id>/', add_ultrasound_for_request, name='add_ultrasound_for_request'),
    path('reject_ultrasound_request/<int:request_id>/', reject_ultrasound_request, name='reject_ultrasound_request'),
]