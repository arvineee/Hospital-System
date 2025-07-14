from django.contrib.auth.models import User
from django.db import models
from patients.models import Patient_register,Billing
# Over the Counter (OTC) Sale model for professional pharmacy OTC sales
class OTCSale(models.Model):
    drug = models.ForeignKey('Drug', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    sale_datetime = models.DateTimeField(auto_now_add=True)
    customer_name = models.CharField("Customer Name (optional)", max_length=100, blank=True)
    customer_contact = models.CharField("Customer Contact (optional)", max_length=50, blank=True)
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Cashier/User who processed the sale")

    def __str__(self):
        return f"OTC Sale: {self.quantity} x {self.drug.name} on {self.sale_datetime.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "OTC Sale"
        verbose_name_plural = "OTC Sales"
        ordering = ['-sale_datetime']

    # Optionally, add a method to get a receipt or summary for reporting
    def get_receipt_summary(self):
        return {
            'drug': self.drug.name,
            'quantity': self.quantity,
            'price_per_unit': self.price_per_unit,
            'total_price': self.total_price,
            'sale_datetime': self.sale_datetime,
            'customer_name': self.customer_name,
            'customer_contact': self.customer_contact,
            'cashier': self.cashier.username if self.cashier else None,
        }


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
    issue_date = models.DateTimeField(auto_now_add=True)
    given = models.BooleanField(default=False)
    bill = models.ForeignKey(Billing, on_delete=models.SET_NULL, null=True, blank=True, related_name='drug_issues_for_bill')


    def __str__(self):
        return f"Issue of {self.drug.name} to {self.patient.name}"

