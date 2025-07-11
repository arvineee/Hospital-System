from django.db import models 
from django.contrib.auth.models import User 

class Patient_register(models.Model):
    name = models.CharField(max_length=100)
    age = models.DecimalField(max_digits=3, decimal_places=1)
    contact = models.IntegerField(null=True, blank=True)
    residence = models.CharField(max_length=255, blank=True)  # New field
    adm_date = models.DateField(auto_now_add=True)
    sex = models.CharField(max_length=10)
    ward = models.CharField(max_length=100, default='OPD')
    prescribed_drug = models.ForeignKey('drugs.Drug', on_delete=models.SET_NULL, null=True, blank=True) 
    is_discharged = models.BooleanField(default=False)
    discharge_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name
    
class PatientHistory(models.Model):

    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    signs = models.TextField(blank=True)
    symptoms = models.TextField(blank=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, blank=True)
    pulse = models.IntegerField(null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    spo2 = models.IntegerField(null=True, blank=True)
    hpi = models.TextField("History of Present Illness", blank=True)
    # Diagnosis and notes come last
    diagnosis = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(blank=True)
    doctor = models.CharField(max_length=100, null=True, blank=True)
    # Status for draft/finalized
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("final", "Finalized"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")


    def __str__(self):
        return f"History for {self.patient.name} on {self.date}"


class Appointment(models.Model):
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    schedule_date = models.DateTimeField()
    purpose = models.TextField()
    status_choices = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled')
    ]
    status = models.CharField(max_length=10, choices=status_choices, default='Scheduled')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - {self.schedule_date.strftime('%Y-%m-%d %H:%M')}"


    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialty}"

# Modern Billing model

# --- Enhanced Billing Model ---
from django.utils import timezone

class Billing(models.Model):
    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("paybill", "Paybill (Mobile Money)")
    ]
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE, related_name='billings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)  # e.g. transaction code
    details = models.JSONField(default=dict, blank=True)  # Store breakdown (medication, lab, ultrasound, etc)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # New: Track status (Paid, Partial, Overdue)
    STATUS_CHOICES = [
        ("paid", "Paid"),
        ("partial", "Partially Paid"),
        ("unpaid", "Unpaid"),
        ("overdue", "Overdue"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="unpaid")

    # New: Overdue flag and due date
    due_date = models.DateField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False)

    # Store PDF receipt as binary (nullable, optional)
    receipt_pdf = models.BinaryField(null=True, blank=True)

    def update_status(self):
        if self.due_amount <= 0:
            self.status = "paid"
            self.is_paid = True
            self.is_overdue = False
        elif self.paid_amount > 0:
            self.status = "partial"
            self.is_paid = False
            self.is_overdue = self.due_date and self.due_date < timezone.now().date()
        else:
            self.status = "unpaid"
            self.is_paid = False
            self.is_overdue = self.due_date and self.due_date < timezone.now().date()
        self.save(update_fields=["status", "is_paid", "is_overdue"])

    def __str__(self):
        return f"Bill for {self.patient.name} on {self.created_at.strftime('%Y-%m-%d')} (Total: {self.total_amount})"

# --- Payment History Model ---
class PaymentHistory(models.Model):
    bill = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name="payment_history")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=Billing.PAYMENT_METHODS)
    payment_reference = models.CharField(max_length=100, blank=True)
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment of {self.paid_amount} for Bill {self.bill.id} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
