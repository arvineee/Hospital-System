from django.db import models



class Ultrasound(models.Model):
    patient = models.CharField(max_length=100)
    date = models.DateField(auto_now_add=True)
    ultrasound_type = models.CharField(max_length=100)
    findings = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='img/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return f"Ultrasound for {self.patient.name} on {self.date}"
    
class UltrasoundRequest(models.Model):
    patient = models.ForeignKey('patients.Patient_register', on_delete=models.CASCADE)
    requested_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    ultrasound = models.ForeignKey(Ultrasound, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    

    def __str__(self):
        return f"Ultrasound Request for {self.patient.name} at {self.requested_at}"