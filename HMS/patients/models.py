from django.db import models

class Patient_register(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    contact = models.IntegerField(null=True)
    adm_date = models.DateField(auto_now_add=True)
    sex = models.CharField(max_length=10)
    prescribed_drug = models.ForeignKey('drugs.Drug', on_delete=models.SET_NULL, null=True, blank=True)  # Use string reference

    def __str__(self):
        return self.name