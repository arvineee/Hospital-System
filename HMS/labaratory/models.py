from django.db import models
from patients.models import Patient_register

class Labaratory(models.Model):
    labaratory_name = models.CharField(max_length=100)
    labaratory_location = models.CharField(max_length=100)
    labaratory_description = models.TextField(blank=True)
    labaratory_phone = models.CharField(max_length=20, blank=True)
    labaratory_email = models.EmailField(blank=True)
    
    def __str__(self):
        return self.labaratory_name

class LabaratoryTest(models.Model):
    labaratory = models.ForeignKey(Labaratory, on_delete=models.CASCADE)
    test_name = models.CharField(max_length=100)
    test_description = models.TextField()
    test_price = models.DecimalField(max_digits=10, decimal_places=2)
    test_duration = models.CharField(max_length=50)  # e.g., "2 hours", "30 minutes"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['test_name']

    def __str__(self):
        return f"{self.test_name} at {self.labaratory.labaratory_name}"


class LabaratoryTestResult(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]
    labaratory_test = models.ForeignKey(LabaratoryTest, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE)
    test_result = models.TextField()
    test_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    
    def __str__(self):
        return f"Result for {self.patient.name} - {self.labaratory_test.test_name}"

class LabaratoryAppointment(models.Model):
    labaratory = models.ForeignKey(Labaratory, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    appointment_reason = models.TextField()
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
    
    def __str__(self):
        return f"Appointment for {self.patient.name} on {self.appointment_date}"