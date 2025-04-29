from django.db import models 

class Patient_register(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    contact = models.IntegerField(null=True)
    adm_date = models.DateField(auto_now_add=True)
    sex = models.CharField(max_length=10)
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