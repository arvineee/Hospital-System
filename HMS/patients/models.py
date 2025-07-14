from django.db import models 
from django.contrib.auth.models import User 

class Patient_register(models.Model):
    name = models.CharField(max_length=100)
    age = models.DecimalField(max_digits=3, decimal_places=1)
    contact = models.IntegerField(null=True, blank=True)
    residence = models.CharField(max_length=255, blank=True) 
    adm_date = models.DateField(auto_now_add=True)
    sex = models.CharField(max_length=10)
    ward = models.CharField(max_length=100, default='OPD')
    prescribed_drug = models.ForeignKey('drugs.Drug', on_delete=models.SET_NULL, null=True, blank=True) 
    is_discharged = models.BooleanField(default=False)
    discharge_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default='Admitted')
    due_date = models.DateField(null=True, blank=True)

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
from decimal import Decimal

class Billing(models.Model):
    patient = models.ForeignKey(Patient_register, on_delete=models.CASCADE, related_name='bills')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, blank=True, null=True) # Max length was 50 previously
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    details = models.JSONField(default=dict, blank=True, null=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    receipt_pdf = models.BinaryField(null=True, blank=True)
    status = models.CharField(max_length=50, default='pending') # e.g., 'pending', 'partial', 'paid', 'overdue'
    is_overdue = models.BooleanField(default=False) # Ensure this has a default

    def update_status(self):
        if self.due_amount <= 0:
            self.status = 'paid'
            self.is_paid = True
            self.is_overdue = False # If paid, it's not overdue
        elif self.paid_amount > 0 and self.due_amount > 0:
            self.status = 'partial'
            self.is_paid = False
        else:
            self.status = 'pending'
            self.is_paid = False
        # Overdue status can also be set by the re_admit logic or a separate check

    def __str__(self):
        return f"Bill {self.id} for {self.patient.name} (Ksh {self.total_amount})"


class PaymentHistory(models.Model):
    # Define payment method choices directly within PaymentHistory or as global constants
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Card Payment'),
        ('insurance', 'Insurance'),
        ('bank_transfer', 'Bank Transfer'),
        ('other', 'Other'),
    ]

    bill = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name='payment_history')
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS) # <--- USE THE DEFINED CHOICES AND MAX_LENGTH
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Payment Histories"
        ordering = ['-timestamp']

    def __str__(self):
        return f"Payment of {self.paid_amount} for Bill {self.bill.id} on {self.timestamp.strftime('%Y-%m-%d')}"
