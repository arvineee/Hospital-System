from django.db import models
from patients.models import Patient_register, Billing



class Ultrasound(models.Model):
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    ultrasound_type = models.CharField(max_length=100)
    findings = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='img/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    bill = models.ForeignKey(Billing, on_delete=models.SET_NULL, null=True, blank=True, related_name='ultrasounds_for_bill')

    

    def __str__(self):
        return f"Ultrasound for {self.patient} on {self.date}"
    
class UltrasoundRequest(models.Model):
    patient = models.ForeignKey('patients.Patient_register', on_delete=models.CASCADE)
    ultrasound_type = models.CharField(max_length=100,default='Abdominal Ultrasound')
    reason = models.TextField(default='Routine check-up')
    priority = models.CharField(max_length=20, choices=[('routine', 'Routine'), ('urgent', 'Urgent'), ('emergency', 'Emergency')], default='routine')
    requester = models.CharField(max_length=100, default='Dr. Felix')
    requester_role = models.CharField(max_length=50, blank=True, null=True)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')
    is_completed = models.BooleanField(default=False)
    ultrasound = models.ForeignKey(Ultrasound, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Ultrasound Request for {self.patient} at {self.request_date}"