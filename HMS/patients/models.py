from django.db import models 
from django.contrib.auth.models import User 

class Patient_register(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    contact = models.IntegerField(null=True)
    adm_date = models.DateField(auto_now_add=True)
    sex = models.CharField(max_length=10)
    ward = models.CharField(max_length=100, default='General Ward')
    prescribed_drug = models.ForeignKey('drugs.Drug', on_delete=models.SET_NULL, null=True, blank=True) 
    is_discharged = models.BooleanField(default=False)
    discharge_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name
    
class PatientHistory(models.Model):
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    diagnosis = models.CharField(max_length=255,null=False)
    notes = models.TextField()
    doctor = models.CharField(max_length=100, null=True, blank=True)


    def __str__(self):
        return f"History for {self.patient.name} on {self.date}"


class Appointment(models.Model):
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    schedule_date = models.DateTimeField()
    purpose = models.TextField()
    status_choices = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled')
    ]
    status = models.CharField(max_length=10, choices=status_choices, default='Scheduled')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - {self.schedule_date.strftime('%Y-%m-%d %H:%M')}"

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialty = models.CharField(max_length=100)
    availability = models.CharField(max_length=200,
                   default="Mon-Fri: 9AM-5PM")
    license_number = models.CharField(max_length=50)
    is_consultant = models.BooleanField(default=False)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialty}"
