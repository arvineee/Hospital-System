from django.db import models

class Patient_register(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    contact = models.IntegerField(null=True)
    adm_date = models.DateField(auto_now_add=True)
    sex = models.CharField(max_length=10)
    
    def __str__(self):
        return self.name