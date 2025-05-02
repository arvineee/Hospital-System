from django.contrib import admin
from .models import Labaratory, LabaratoryTest, LabaratoryTestResult, LabaratoryAppointment

# Register your models here.
admin.site.register(Labaratory)
admin.site.register(LabaratoryTest)
admin.site.register(LabaratoryTestResult)
admin.site.register(LabaratoryAppointment)
