from django.db import models
from patients.models import Patient_register  


class Drug(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    expiry_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class DrugIssue(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE)  # Foreign key to Patient_register
    quantity_issued = models.IntegerField()
    issue_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Issue of {self.drug.name} to {self.patient.name}"