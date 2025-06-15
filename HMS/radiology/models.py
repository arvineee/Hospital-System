from django.db import models



class Ultrasound(models.Model):
    patient = models.CharField(max_length=100)
    date = models.DateField(auto_now_add=True)
    ultrasound_type = models.CharField(max_length=100)
    findings = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='ultrasound_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return f"Ultrasound for {self.patient.name} on {self.date}"