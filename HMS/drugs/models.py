from django.contrib.auth.models import User
from django.db import models
from patients.models import Patient_register,Billing
from django.utils import timezone
from datetime import timedelta




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
    reorder_level = models.IntegerField(default=10, help_text="Quantity at which to trigger a low stock alert")
    unit_of_measure = models.CharField(max_length=50, default='tablets', help_text="e.g., tablets, ml, vials, sachets")
    
    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    @property
    def is_expiring_soon(self):
        # Define 'soon' as 3 months (adjust as needed)
        return self.expiry_date <= timezone.now().date() + timedelta(days=90)


class DrugIssue(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE)  # Foreign key to Patient_register
    quantity_issued = models.IntegerField()
    issue_date = models.DateTimeField(auto_now_add=True)
    given = models.BooleanField(default=False)
    bill = models.ForeignKey(Billing, on_delete=models.SET_NULL, null=True, blank=True, related_name='drug_issues_for_bill')


    def __str__(self):
        return f"Issue of {self.drug.name} to {self.patient.name}"
    

class Prescription(models.Model):
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE, related_name='prescriptions')
    prescribed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Doctor who prescribed")
    prescription_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True, help_text="General notes for the prescription")
    is_fulfilled = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Prescription for {self.patient.name} on {self.prescription_date.strftime('%Y-%m-%d')}"

# New model for Prescription Items (drugs within a prescription)
class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg, 2 tablets")
    frequency = models.CharField(max_length=100, help_text="e.g., twice daily, every 8 hours")
    duration = models.CharField(max_length=100, help_text="e.g., 7 days, until finished")
    instructions = models.TextField(blank=True, null=True, help_text="Specific instructions for the patient")
    
    
    def __str__(self):
        return f"{self.drug.name} - {self.dosage}, {self.frequency} for {self.prescription.patient.name}"

# New model for Supplier Management
class DrugSupplier(models.Model):
    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

# New model for Drug Orders from Suppliers
class DrugOrder(models.Model):
    supplier = models.ForeignKey(DrugSupplier, on_delete=models.PROTECT, related_name='orders')
    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField(blank=True, null=True)
    status_choices = [
        ('pending', 'Pending'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='pending')
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Order {self.id} from {self.supplier.name} ({self.status})"

# New model for items within a Drug Order
class DrugOrderItem(models.Model):
    order = models.ForeignKey(DrugOrder, on_delete=models.CASCADE, related_name='items')
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT) # Don't delete drug if it's in an order
    quantity_ordered = models.PositiveIntegerField()
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity_ordered} x {self.drug.name} for Order {self.order.id}"

    @property
    def item_total(self):
        return self.quantity_ordered * self.cost_per_unit


class StockAdjustment(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="User who made the adjustment")
    initial_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    reason = models.TextField(blank=True, null=True, help_text="Reason for the adjustment (e.g., physical count, spoilage)")

    def __str__(self):
        return f"Adjustment for {self.drug.name} on {self.adjustment_date.strftime('%Y-%m-%d')}"
