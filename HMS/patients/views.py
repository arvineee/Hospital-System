from django.contrib.admin.views.decorators import staff_member_required

# --- Analytics Dashboard View ---
@staff_member_required
def analytics_dashboard(request):
    from patients.models import Patient_register
    from drugs.models import OTCSale
    from labaratory.models import LabaratoryTestResult
    from django.contrib.auth.models import User
    from django.db.models import Count, Sum
    from datetime import datetime, timedelta
    from django.utils import timezone

    # KPIs
    total_patients = Patient_register.objects.count()
    total_staff = User.objects.filter(is_staff=True).count()
    today = timezone.localdate()
    otc_sales_today = OTCSale.objects.filter(sale_datetime__date=today).count()
    # Lab tests this month
    first_of_month = today.replace(day=1)
    # If test_date is a DateTimeField, use __gte directly
    lab_tests_month = LabaratoryTestResult.objects.filter(test_date__gte=first_of_month).count()

    # Admissions last 30 days
    last_30 = today - timedelta(days=29)
    # If adm_date is a DateField or DateTimeField, use __gte directly (no __date)
    admissions = Patient_register.objects.filter(adm_date__gte=last_30)
    from django.db.models.functions import TruncDate
    admissions_by_day = admissions.annotate(day=TruncDate('adm_date')).values('day').annotate(count=Count('id')).order_by('day')
    admissions_labels = [a['day'].strftime('%b %d') for a in admissions_by_day]
    admissions_data = [a['count'] for a in admissions_by_day]

    # Revenue breakdown (this month)
    from patients.models import Billing
    bills = Billing.objects.filter(created_at__date__gte=first_of_month)
    revenue_labels = ['Consultation', 'Medication', 'Lab', 'Ultrasound', 'Other']
    revenue_data = [
        sum(float(b.details.get('consultation_charge', 0)) for b in bills),
        sum(float(b.details.get('medication_charge', 0)) for b in bills),
        sum(float(b.details.get('laboratory_charge', 0)) for b in bills),
        sum(float(b.details.get('ultrasound_charge', 0)) for b in bills),
        sum(float(b.details.get('room_charge', 0)) for b in bills),
    ]

    # Lab tests trend (last 6 months)
    from dateutil.relativedelta import relativedelta
    lab_trend_labels = []
    lab_trend_data = []
    for i in range(5, -1, -1):
        month = today - relativedelta(months=i)
        label = month.strftime('%b %Y')
        count = LabaratoryTestResult.objects.filter(test_date__year=month.year, test_date__month=month.month).count()
        lab_trend_labels.append(label)
        lab_trend_data.append(count)

    context = {
        'total_patients': total_patients,
        'total_staff': total_staff,
        'lab_tests_month': lab_tests_month,
        'otc_sales_today': otc_sales_today,
        'admissions_labels': admissions_labels,
        'admissions_data': admissions_data,
        'revenue_labels': revenue_labels,
        'revenue_data': revenue_data,
        'lab_tests_labels': lab_trend_labels,  # renamed for template JS
        'lab_tests_data': lab_trend_data,      # renamed for template JS
    }
    return render(request, 'analytics/dashboard.html', context)

from .models import Billing, PaymentHistory
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.mail import mail_admins
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from .models import Patient_register, PatientHistory,Appointment
from drugs.models import DrugIssue
from django.contrib.auth.decorators import login_required
from drugs.models import Drug, DrugIssue 
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from labaratory.models import Labaratory
from labaratory.models import LabaratoryTestResult, LabaratoryTest
from radiology.models import Ultrasound
from django.utils import timezone
from datetime import datetime,timedelta
from django.db.models import Q 
import logging
from radiology.models import UltrasoundRequest

logger = logging.getLogger(__name__)



@login_required
@require_http_methods(["GET", "POST"])
def update_payment(request, bill_id):
    from decimal import Decimal
    bill = get_object_or_404(Billing, id=bill_id)
    patient = bill.patient
    if request.method == "POST":
        try:
            paid_amount = Decimal(request.POST.get("paid_amount", 0))
            payment_method = request.POST.get("payment_method", "")
            payment_reference = request.POST.get("payment_reference", "")
            # Validation
            if paid_amount < 0 or paid_amount > bill.total_amount:
                messages.error(request, "Invalid payment amount.")
                return render(request, "patients/update_payment.html", {"bill": bill, "patient": patient})
            # Record payment history
            PaymentHistory.objects.create(
                bill=bill,
                paid_amount=paid_amount,
                payment_method=payment_method,
                payment_reference=payment_reference,
                paid_by=request.user
            )
            # Update bill
            bill.paid_amount += paid_amount
            bill.due_amount = bill.total_amount - bill.paid_amount
            bill.payment_method = payment_method
            bill.payment_reference = payment_reference
            bill.updated_at = timezone.now()
            bill.update_status()
            # If fully paid, mark as paid and clear due
            if bill.due_amount <= 0:
                bill.is_paid = True
                bill.due_amount = 0
            bill.save(update_fields=["paid_amount", "due_amount", "payment_method", "payment_reference", "updated_at", "is_paid", "status"])

            # --- Notify Admins on Payment ---
            try:
                Hospital_name = getattr(settings, 'HOSPITAL_NAME', 'HMS Hospital System')
                from django.core.mail import EmailMultiAlternatives
                from io import BytesIO
                from reportlab.lib.pagesizes import A5
                from reportlab.lib import colors
                from reportlab.lib.units import mm
                from reportlab.pdfgen import canvas
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.platypus import Paragraph, Table, TableStyle, SimpleDocTemplate, Spacer
                subject = f"[{Hospital_name}] Payment Received for {patient.name} (Bill #{bill.id})"
                text_message = (
                    f"A payment has been made for patient: {patient.name}\n"
                    f"Patient ID: {patient.id}\n"
                    f"Bill ID: {bill.id}\n"
                    f"Amount Paid: {paid_amount}\n"
                    f"Payment Method: {payment_method}\n"
                    f"Payment Reference: {payment_reference}\n"
                    f"Paid By: {request.user.get_full_name() or request.user.username}\n"
                    f"Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Current Bill Status: {bill.status}\n"
                    f"Total Amount: {bill.total_amount}\n"
                    f"Paid Amount: {bill.paid_amount}\n"
                    f"Due Amount: {bill.due_amount}\n"
                )
                html_message = f"""
                <html>
                <body style='font-family: Arial, sans-serif; color: #222;'>
                    <h2 style='color: #1976d2;'>Payment Received for {patient.name}</h2>
                    <table style='border-collapse: collapse;'>
                        <tr><td><b>Patient ID:</b></td><td>{patient.id}</td></tr>
                        <tr><td><b>Bill ID:</b></td><td>{bill.id}</td></tr>
                        <tr><td><b>Amount Paid:</b></td><td style='color: #388e3c;'>Ksh {paid_amount}</td></tr>
                        <tr><td><b>Payment Method:</b></td><td>{payment_method}</td></tr>
                        <tr><td><b>Payment Reference:</b></td><td>{payment_reference}</td></tr>
                        <tr><td><b>Paid By:</b></td><td>{request.user.get_full_name() or request.user.username}</td></tr>
                        <tr><td><b>Date:</b></td><td>{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                        <tr><td><b>Current Bill Status:</b></td><td>{bill.status}</td></tr>
                        <tr><td><b>Total Amount:</b></td><td>Ksh {bill.total_amount}</td></tr>
                        <tr><td><b>Paid Amount:</b></td><td>Ksh {bill.paid_amount}</td></tr>
                        <tr><td><b>Due Amount:</b></td><td style='color: #d32f2f;'>Ksh {bill.due_amount}</td></tr>
                    </table>
                </body>
                </html>
                """
                # Generate modern PDF receipt (A5 size, branding, table, clear layout)
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A5, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
                styles = getSampleStyleSheet()
                elements = []
                elements.append(Paragraph("<b>HMS Hospital System</b>", styles['Title']))
                elements.append(Spacer(1, 6 * mm))
                elements.append(Paragraph(f"<b>Payment Receipt</b>", styles['Heading2']))
                elements.append(Spacer(1, 4 * mm))
                elements.append(Paragraph(f"<b>Date:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
                elements.append(Spacer(1, 2 * mm))
                # Patient and Bill Info Table
                data = [
                    ["Patient Name", patient.name],
                    ["Patient ID", patient.id],
                    ["Bill ID", bill.id],
                    ["Amount Paid", f"Ksh {paid_amount}"],
                    ["Payment Method", payment_method],
                    ["Payment Reference", payment_reference],
                    ["Paid By", request.user.get_full_name() or request.user.username],
                    ["Current Bill Status", bill.status],
                    ["Total Amount", f"Ksh {bill.total_amount}"],
                    ["Paid Amount", f"Ksh {bill.paid_amount}"],
                    ["Due Amount", f"Ksh {bill.due_amount}"],
                ]
                table = Table(data, colWidths=[80*mm, 60*mm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(table)
                elements.append(Spacer(1, 8 * mm))
                elements.append(Paragraph("Thank you for your payment!", styles['Italic']))
                doc.build(elements)
                pdf_data = buffer.getvalue()
                buffer.close()
                from django.conf import settings
                admin_emails = [email for _, email in getattr(settings, 'ADMINS', [('Admin', 'admin@example.com')])]
                msg = EmailMultiAlternatives(subject, text_message, settings.DEFAULT_FROM_EMAIL, admin_emails)
                msg.attach_alternative(html_message, "text/html")
                msg.attach(f"receipt_bill_{bill.id}.pdf", pdf_data, "application/pdf")
                msg.send(fail_silently=True)
                # Save PDF to Billing model for future download
                bill.receipt_pdf = pdf_data
                bill.save(update_fields=["receipt_pdf"])
                # Also keep in session for immediate download
                request.session['last_receipt_pdf'] = pdf_data.hex()
                request.session.modified = True
                request.session.save()
            except Exception as notify_exc:
                # Log or print error, but don't block payment
                print(f"Admin notification failed: {notify_exc}")

            messages.success(request, "Payment status updated successfully.")
            pdf_url = reverse('download_receipt', args=[bill.id])
            profile_url = reverse('pat_view', args=[patient.id])
            return render(request, "patients/payment_success_download.html", {
                "pdf_url": pdf_url,
                "pdf_filename": f"receipt_bill_{bill.id}.pdf",
                "profile_url": profile_url,
            })
        except Exception as e:
            messages.error(request, f"Error updating payment: {str(e)}")
            print(e)
    # Get payment history for display
    payment_history = bill.payment_history.order_by('-timestamp')
    return render(request, "patients/update_payment.html", {"bill": bill, "patient": patient, "payment_history": payment_history})

from django.http import HttpResponse
import binascii
from django.views.decorators.http import require_GET

# Serve PDF receipt for download after payment
@require_GET
def download_receipt(request, bill_id):
    # Try session first for immediate download after payment
    pdf_hex = request.session.get('last_receipt_pdf')
    pdf_data = None
    if pdf_hex:
        try:
            pdf_data = binascii.unhexlify(pdf_hex)
        except Exception:
            pdf_data = None
    # If not in session, try from Billing model
    if not pdf_data:
        from .models import Billing
        bill = Billing.objects.filter(id=bill_id).first()
        if bill and bill.receipt_pdf:
            pdf_data = bill.receipt_pdf
        else:
            return HttpResponse('No receipt available.', status=404)
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_bill_{bill_id}.pdf"'
    return response
def all_patients(request):
    patients = Patient_register.objects.all()
    return render(request, 'patients/home.html', {'patients': patients})
def pat_register(request):
    try:
        if request.method == 'POST':
            # Retrieve form data
            name = request.POST.get('name', '').strip()
            age = request.POST.get('age')
            contact = request.POST.get('contact')
            ward = request.POST.get('ward')
            sex = request.POST.get('sex')

            # Validate required fields
            if not all([name, age, contact, sex]):
                messages.error(request, "All fields are required.")
                return render(request, 'patients/register.html')

            # Validate age and contact
            try:
                age = int(age)
                contact = int(contact)
                if age <= 0 or age > 150:
                    messages.error(request, "Please enter a valid age.")
                    return render(request, 'patients/register.html')
            except ValueError:
                messages.error(request, "Age and contact must be valid numbers.")
                return render(request, 'patients/register.html')

            # Check for duplicate patient
            if Patient_register.objects.filter(name=name, contact=contact).exists():
                messages.error(request, "Patient with this name and contact already exists.")
                return render(request, 'patients/register.html')

            # Create and save the new patient
            new_patient = Patient_register(
                name=name,
                age=age,
                contact=contact,
                ward=ward,
                sex=sex,
                adm_date=datetime.now().date()
            )
            new_patient.save()

            messages.success(request, f"Patient {name} successfully registered.")
            return redirect('pat_view', id=new_patient.id)

        # If GET request, render the registration form
        return render(request, 'patients/register.html')

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return render(request, 'patients/register.html')

def pat_update(request, id):
    try:
        patient = get_object_or_404(Patient_register, id=id)
        
        if request.method == 'POST':
            # Retrieve form data
            name = request.POST.get('name', '').strip()
            age = request.POST.get('age')
            contact = request.POST.get('contact')
            sex = request.POST.get('sex')
            ward = request.POST.get('ward')

            # Validate required fields
            if not all([name, age, contact, sex]):
                messages.error(request, "All fields are required.")
                return render(request, 'patients/update.html', {'patient': patient})

            # Validate age and contact
            try:
                age = int(age)
                contact = int(contact)
                if age <= 0 or age > 150:
                    messages.error(request, "Please enter a valid age.")
                    return render(request, 'patients/update.html', {'patient': patient})
            except ValueError:
                messages.error(request, "Age and contact must be valid numbers.")
                return render(request, 'patients/update.html', {'patient': patient})

            # Check for duplicate patient
            if Patient_register.objects.filter(name=name, contact=contact).exclude(id=id).exists():
                messages.error(request, "Patient with this name and contact already exists.")
                return render(request, 'patients/update.html', {'patient': patient})

            # Update the patient details
            patient.name = name
            patient.age = age
            patient.contact = contact
            patient.sex = sex
            patient.ward = ward
            patient.save()

            messages.success(request, f"Patient {name}'s details successfully updated.")
            return redirect('pat_view', id=patient.id)

        # If GET request, render the update form with existing patient data
        return render(request, 'patients/update.html', {'patient': patient})

    except Patient_register.DoesNotExist:
        messages.error(request, "Patient not found.")
        return redirect('all_patients')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return render(request, 'patients/update.html', {'patient': patient})
def pat_delete(request, id):
    patient = Patient_register.objects.get(id=id)
    if request.method == 'POST':
        # Delete the patient
        patient.delete()
        messages.success(request, "Patient successfully deleted.")
        return redirect(all_patients)
    # If GET request, render the delete confirmation page
    return render(request, 'patients/delete.html', {'patient': patient})  
def pat_search(request):
    name = request.GET.get('name', '').strip()  # Get the 'name' parameter from the request
    if name:
        # Perform a case-insensitive search
        patients = Patient_register.objects.filter(name__icontains=name)
        if patients.exists():
            return render(request, 'patients/search_results.html', {'patients': patients})
        else:
            messages.error(request, "No patient found with the given name.")
            return redirect('all_patients')  # Redirect to the patient list if no results are found
    else:
        messages.error(request, "Please enter a name to search.")
        return redirect('all_patients')  # Redirect to the patient list if no name is provided 
    
def pat_view(request, id):
    patient = get_object_or_404(Patient_register, id=id)
    labaratories = Labaratory.objects.all()
    # Add available lab tests for request
    from labaratory.models import LabaratoryTest
    available_tests = LabaratoryTest.objects.all()
    return render(request, 'patients/view.html', {
        'patient': patient,
        'labaratories': labaratories,
        'available_tests': available_tests
    })

def prescribe_drugs(request, id):
    patient = Patient_register.objects.get(id=id)
    drugs = Drug.objects.all()  # Fetch all available drugs

    if request.method == 'POST':
        # Retrieve form data
        drug_ids = request.POST.getlist('drug_ids')  # Get list of selected drug IDs
        quantities = request.POST.getlist('quantities')  # Get list of quantities

        # Validate required fields
        if not drug_ids or not quantities or len(drug_ids) != len(quantities):
            messages.error(request, "All fields are required.")
            return render(request, 'patients/prescribe_drugs.html', {'patient': patient, 'drugs': drugs})

        # Process each drug and quantity
        for drug_id, quantity in zip(drug_ids, quantities):
            try:
                drug = Drug.objects.get(id=drug_id)
                quantity = int(quantity)

                # Check if the drug has enough stock
                if drug.quantity < quantity:
                    messages.error(request, f"Not enough stock for {drug.name}.")
                    return render(request, 'patients/prescribe_drugs.html', {'patient': patient, 'drugs': drugs})

                # Deduct the quantity from the drug stock
                drug.quantity -= quantity
                drug.save()

                # Create a DrugIssue record
                DrugIssue.objects.create(drug=drug, patient=patient, quantity_issued=quantity)

            except Drug.DoesNotExist:
                messages.error(request, "Invalid drug selected.")
                return render(request, 'patients/prescribe_drugs.html', {'patient': patient, 'drugs': drugs})

        # Redirect or return success response
        messages.success(request, "Drugs successfully prescribed.")
        return redirect(pat_view, id=id)  # Redirect to the patient's view page

    # If GET request, render the prescribe drugs form
    return render(request, 'patients/prescribe_drugs.html', {'patient': patient, 'drugs': drugs})
def drug_issued(request, id=None):
    if id:
        # Fetch all drug issues for the specific patient
        drug_issues = DrugIssue.objects.filter(patient_id=id)
        patient = Patient_register.objects.get(id=id)
        return render(request, 'patients/drug_issued.html', {'drug_issues': drug_issues, 'patient': patient})
    
    # If no ID is provided, fetch all drug issues
    drug_issues = DrugIssue.objects.all()
    return render(request, 'patients/drug_issued.html', {'drug_issues': drug_issues})
def drug_issue(request):
    if request.method == 'POST':
        drug_id = request.POST.get('drug_id')
        quantity_issued = request.POST.get('quantity_issued')

        # Validate required fields
        if not all([drug_id, quantity_issued]):
            messages.error(request,"All fields are required.")
            return render(request, 'drugs/issue_drug.html')

        # Check if drug exists
        try:
            drug = Drug.objects.get(id=drug_id)
        except Drug.DoesNotExist:
            messages.error(request,"Drug does not exist.")
            return render(request, 'drugs/issue_drug.html')
        
def patient_discharge(request, id):
    patient = Patient_register.objects.get(id=id)
    if request.method == 'POST':
        # Update the patient's discharge status
        patient.is_discharged = True
        patient.discharge_date = request.POST.get('discharge_date')
        patient.save()
        messages.success(request, "Patient successfully discharged.")
        return redirect(pat_view, id=id)  # Redirect to the patient's view page
    return render(request, 'patients/discharge.html', {'patient': patient})

def re_admit(request, id):
    try:
        patient = Patient_register.objects.get(id=id)
        
        # Check if patient is already admitted
        if not patient.is_discharged:
            messages.error(request, "Patient is already admitted.")
            return redirect('all_patients')
        
        # --- BILLING LOGIC ON RE-ADMISSION ---
        from .models import Billing
        from decimal import Decimal
        # Find any unpaid/partially paid bill
        pending_bills = Billing.objects.filter(patient=patient, is_paid=False)
        if pending_bills.exists():
            # There is a pending bill, so add its due to the new bill and mark as combined
            pending_total_due = sum(b.due_amount for b in pending_bills)
            # Optionally, mark old bills as combined/archived (customize as needed)
            for b in pending_bills:
                b.status = 'overdue'
                b.save(update_fields=["status"])
            # Set new admission date (use full datetime for accuracy)
            from datetime import datetime
            patient.is_discharged = False
            patient.discharge_date = None
            patient.adm_date = datetime.now()
            patient.save()
            # Create a new bill with the pending due clearly indicated in details
            details = {
                'previous_pending_due': float(pending_total_due),
                'note': 'Includes previous unpaid bill(s) due on re-admission.'
            }
            new_bill = Billing.objects.create(
                patient=patient,
                total_amount=Decimal('0.00'),  # Will be updated on next billing calculation
                paid_amount=Decimal('0.00'),
                due_amount=pending_total_due,
                is_paid=False,
                details=details,
                generated_by=request.user if request.user.is_authenticated else None,
                status='unpaid',
            )
            messages.warning(request, f"Patient re-admitted. Previous unpaid bill(s) of KSH {pending_total_due:.2f} carried forward and added to new bill.")
        else:
            # All bills cleared, so start fresh
            from datetime import datetime
            patient.is_discharged = False
            patient.discharge_date = None
            patient.adm_date = datetime.now()
            patient.save()
            # Create a new bill (empty, will be updated on next billing)
            Billing.objects.create(
                patient=patient,
                total_amount=Decimal('0.00'),
                paid_amount=Decimal('0.00'),
                due_amount=Decimal('0.00'),
                is_paid=False,
                details={'note': 'New bill on re-admission. All previous bills cleared.'},
                generated_by=request.user if request.user.is_authenticated else None,
                status='unpaid',
            )
            messages.success(request, "Patient successfully re-admitted. All previous bills were cleared. New bill started.")
        return redirect('pat_view', id=id)  # Redirect to the patient's view page
    
    except Patient_register.DoesNotExist:
        messages.error(request, "Patient not found.")
        return redirect('all_patients')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('all_patients')

def billing(request, id):
    from .models import Billing
    try:
        patient = get_object_or_404(Patient_register, id=id)
        # Only include charges after the latest admission date (use full datetime for accuracy)
        adm_datetime = patient.adm_date if hasattr(patient, 'adm_date') else None
        drug_issues = DrugIssue.objects.filter(patient=patient, issue_date__gte=adm_datetime)
        lab_results = LabaratoryTestResult.objects.filter(patient=patient, test_date__gte=adm_datetime)
        ultrasounds = Ultrasound.objects.filter(patient=patient.name, created_at__gte=adm_datetime)

        # Calculate billing period
        admission_date = patient.adm_date
        from datetime import datetime
        current_date = datetime.now().date()
        # If adm_date is datetime, use date part for days_admitted
        if isinstance(admission_date, datetime):
            days_admitted = (current_date - admission_date.date()).days or 1
        else:
            days_admitted = (current_date - admission_date).days or 1

        # Charges (use Decimal for all monetary values)
        from decimal import Decimal
        consultation_charge = Decimal('100.00')
        daily_room_charge = Decimal('0.00')
        total_room_charge = daily_room_charge * Decimal(days_admitted)
        medication_total = sum(Decimal(str(issue.drug.price)) * issue.quantity_issued for issue in drug_issues)
        laboratory_total = sum(Decimal(str(result.labaratory_test.test_price)) for result in lab_results)
        ultrasound_total = sum(Decimal(str(us.price)) for us in ultrasounds)
        total = consultation_charge + total_room_charge + medication_total + laboratory_total + ultrasound_total

        # Use the latest bill for this patient
        bill_obj = Billing.objects.filter(patient=patient).order_by('-created_at').first()
        # If this bill has a previous_pending_due, add it to the total
        from decimal import Decimal
        previous_pending_due = Decimal('0.00')
        if bill_obj and bill_obj.details and bill_obj.details.get('previous_pending_due'):
            previous_pending_due = Decimal(str(bill_obj.details['previous_pending_due']))

        # Prepare details for Billing model
        details = {
            'consultation_charge': float(consultation_charge),
            'room_charge': float(total_room_charge),
            'medication_charge': float(medication_total),
            'laboratory_charge': float(laboratory_total),
            'ultrasound_charge': float(ultrasound_total),
            'days_admitted': days_admitted,
            'daily_room_rate': float(daily_room_charge),
        }
        if previous_pending_due and previous_pending_due != Decimal('0.00'):
            # Only show previous_pending_due if it is still actually due (not already paid off)
            if previous_pending_due > 0:
                details['previous_pending_due'] = float(previous_pending_due)
                details['note'] = bill_obj.details.get('note', 'Includes previous unpaid bill(s) due on re-admission.')

        # Add previous pending due to the total
        total_with_pending = total + previous_pending_due

        bill_changed = False
        if bill_obj:
            # Always update bill with latest totals/details
            if bill_obj.total_amount != total_with_pending or bill_obj.details != details:
                bill_obj.total_amount = total_with_pending
                bill_obj.details = details
                # If the new total is greater than paid, mark as unpaid and update due
                if bill_obj.paid_amount < total_with_pending:
                    bill_obj.is_paid = False
                    bill_obj.due_amount = total_with_pending - bill_obj.paid_amount
                else:
                    bill_obj.due_amount = 0
                    bill_obj.is_paid = True
                bill_obj.save(update_fields=["total_amount", "due_amount", "details", "is_paid"])
                bill_changed = True
        else:
            # No bill exists, create a new one
            bill_obj = Billing.objects.create(
                patient=patient,
                total_amount=total_with_pending,
                paid_amount=Decimal('0.00'),
                due_amount=total_with_pending,
                is_paid=False,
                details=details,
                generated_by=request.user if request.user.is_authenticated else None,
            )

        # Prepare context for template
        payment_history = bill_obj.payment_history.order_by('-timestamp')
        # Only redirect if bill is truly fully paid and up-to-date
        if bill_obj.is_paid and bill_obj.due_amount <= 0 and not bill_changed:
            messages.success(request, "This bill is fully paid. No outstanding charges remain.")
            return redirect('pat_view', id=patient.id)
        context = {
            'patient': patient,
            'drug_issues': drug_issues,
            'lab_results': lab_results,
            'ultrasounds': ultrasounds,
            'bill': bill_obj,
            'admission_date': admission_date,
            'current_date': current_date,
            'payment_history': payment_history,
        }
        # Provide PDF receipt for patient if available
        import base64
        receipt_pdf = request.session.get('last_receipt_pdf', None)
        if receipt_pdf:
            context['receipt_pdf'] = base64.b64encode(bytes.fromhex(receipt_pdf)).decode('utf-8')
        return render(request, 'patients/billing.html', context)
    except Patient_register.DoesNotExist:
        messages.error(request, "Patient not found.")
        return redirect('all_patients')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('all_patients')
def patient_history(request, id):
    try:
        patient = Patient_register.objects.get(id=id)
    except Patient_register.DoesNotExist:
        messages.error(request, "Patient not found.")
        return redirect('all_patients')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('all_patients')

    drugs = Drug.objects.all()
    history = PatientHistory.objects.filter(patient=patient).order_by('-date')
    from .forms import PatientHistoryForm
    if request.method == 'POST':
        form = PatientHistoryForm(request.POST)
        if form.is_valid():
            history_entry = form.save(commit=False)
            history_entry.patient = patient
            history_entry.doctor = request.user.get_full_name() or str(request.user)
            history_entry.save()
            messages.success(request, "Patient history successfully updated.")
            return redirect('patient_history', id=id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PatientHistoryForm()

    return render(request, 'patients/patient_history.html', {
        'patient': patient,
        'history': history,
        'form': form,
        'doctor': request.user,
    })


def edit_patient_history(request, history_id):
    history_entry = get_object_or_404(PatientHistory, id=history_id)
    if request.method == 'POST':
        # Get all fields from POST
        history_entry.signs = request.POST.get('signs', '')
        history_entry.symptoms = request.POST.get('symptoms', '')
        history_entry.temperature = request.POST.get('temperature') or None
        history_entry.blood_pressure = request.POST.get('blood_pressure', '')
        history_entry.pulse = request.POST.get('pulse') or None
        history_entry.respiratory_rate = request.POST.get('respiratory_rate') or None
        history_entry.spo2 = request.POST.get('spo2') or None
        history_entry.hpi = request.POST.get('hpi', '')
        history_entry.diagnosis = request.POST.get('diagnosis', '')
        history_entry.notes = request.POST.get('notes', '')
        history_entry.status = request.POST.get('status', 'draft')
        history_entry.save()
        messages.success(request, "Patient history updated.")
        return redirect('patient_history', id=history_entry.patient.id)
    return render(request, 'patients/edit_patient_history.html', {
        'history_entry': history_entry,
    })

@login_required
def schedule_appointment(request, patient_id=None):
    patient = None
    if patient_id:
        patient = get_object_or_404(Patient_register, id=patient_id)
    
    # Get qualified doctors (medical staff or in Doctors group)
    doctors = User.objects.filter(
        Q(groups__name='Doctors') | 
        Q(is_staff=True)
    ).distinct().order_by('last_name')
    
    default_time = datetime.now().strftime('%Y-%m-%dT%H:%M')
    context = {
        'patient': patient,
        'doctors': doctors,
        'default_time': default_time,
        'min_date': datetime.now().strftime('%Y-%m-%d'),
        'max_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    }

    if request.method == 'POST':
        try:
            # Validate required fields
            required_fields = ['patient_id', 'doctor', 'schedule_date', 'purpose']
            if not all(request.POST.get(field) for field in required_fields):
                messages.error(request, "All fields are required")
                return render(request, 'patients/schedule_form.html', context)

            # Get form data
            patient_id = request.POST.get('patient_id')
            doctor_id = request.POST.get('doctor')
            schedule_date_str = request.POST.get('schedule_date')
            purpose = request.POST.get('purpose').strip()

            # Convert datetime
            schedule_date = datetime.strptime(schedule_date_str, '%Y-%m-%dT%H:%M')
            
            # Validate patient
            patient = get_object_or_404(Patient_register, id=patient_id)
            
            # Validate doctor
            doctor = get_object_or_404(User, id=doctor_id)
            if not doctor.groups.filter(name='Doctors').exists() and not doctor.is_staff:
                messages.error(request, "Selected user is not a qualified doctor")
                return render(request, 'patients/schedule_form.html', context)

            # Check scheduling conflict
            if Appointment.objects.filter(
                doctor=doctor,
                schedule_date__date=schedule_date.date(),
                schedule_date__hour=schedule_date.hour
            ).exists():
                messages.error(request, "Doctor has conflicting appointment in this time slot")
                return render(request, 'patients/schedule_form.html', context)

            # Check valid schedule time (8AM-6PM)
            if not (8 <= schedule_date.hour < 18):
                messages.error(request, "Appointments only available between 8AM and 6PM")
                return render(request, 'patients/schedule_form.html', context)

            # Create appointment
            Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                schedule_date=schedule_date,
                purpose=purpose,
                created_by=request.user
            )

            messages.success(request, 
                f"Appointment scheduled with Dr. {doctor.last_name} "
                f"on {schedule_date.strftime('%b %d, %Y at %I:%M %p')}"
            )
            return redirect('view_appointments')

        except ValueError as e:
            messages.error(request, f"Invalid date/time format: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error scheduling appointment: {str(e)}")
            logger.error(f"Appointment scheduling error: {str(e)}")

    return render(request, 'patients/schedule_form.html', context)

@login_required
def view_appointments(request):
    # For doctors: show their appointments
    if request.user.groups.filter(name='Doctors').exists():
        appointments = Appointment.objects.filter(doctor=request.user)
    # For patients: show their appointments
    elif hasattr(request.user, 'patient_profile'):
        appointments = Appointment.objects.filter(patient=request.user.patient_profile)
    # For admins: show all appointments
    else:
        appointments = Appointment.objects.all()
    
    return render(request, 'patients/appointment_list.html', {
        'appointments': appointments.order_by('schedule_date')
    })

@login_required
def update_appointment_status(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Appointment.status_choices):
            appointment.status = new_status
            appointment.save()
            messages.success(request, "Appointment status updated successfully!")
            return redirect('view_appointments')
    
    return render(request, 'patients/update_appointment_status.html', {
        'appointment': appointment,
        'today': timezone.now().strftime('%Y-%m-%d'),
        'status_choices': Appointment.status_choices
    })

@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        appointment.delete()
        messages.success(request, "Appointment cancelled successfully!")
        return redirect('view_appointments')
    
    return render(request, 'patients/cancel_appointment.html', {
        'appointment': appointment
    })

@login_required
def view_patient_ultrasounds(request, patient_id):
    patient = get_object_or_404(Patient_register, id=patient_id)
    ultrasounds = Ultrasound.objects.filter(patient=patient).order_by('-date')
    
    return render(request, 'patients/patient_ultrasounds.html', {
        'patient': patient,
        'ultrasounds': ultrasounds
    })


@login_required
def request_ultrasound(request, patient_id):
    patient = get_object_or_404(Patient_register, id=patient_id)
    requests = UltrasoundRequest.objects.filter(patient=patient).order_by('-request_date')
    if request.method == 'POST':
        ultrasound_type = request.POST.get('ultrasound_type')
        reason = request.POST.get('reason')
        priority = request.POST.get('priority')
        comments = request.POST.get('comments', '')
        requester = request.user.username
        requester_role = getattr(request.user, 'role', '') if hasattr(request.user, 'role') else ''
        # Save the request
        ultrasound_request = UltrasoundRequest.objects.create(
            patient=patient,
            ultrasound_type=ultrasound_type,
            reason=reason,
            priority=priority,
            requester=requester,
            requester_role=requester_role,
            notes=comments,
            status='pending'
        )
        messages.success(request, f"Ultrasound request for {ultrasound_type} has been created for {patient.name}.")
        return redirect('view_patient_ultrasounds', patient_id=patient.id)
    return render(request, 'patients/request_ultrasound.html', {'patient': patient})

def request_lab_test(request, patient_id):
    patient = get_object_or_404(Patient_register, id=patient_id)
    available_tests = LabaratoryTest.objects.all()
    if request.method == 'POST':
        test_id = request.POST.get('test_id')
        notes = request.POST.get('notes', '')
        test = get_object_or_404(LabaratoryTest, id=test_id)
        # Create a pending test result as a request
        LabaratoryTestResult.objects.create(
            labaratory_test=test,
            patient=patient,
            test_result='',
            notes=notes,
            status='Pending'
        )
        messages.success(request, f"Lab test '{test.test_name}' requested for {patient.name}.")
        return redirect('pat_view', id=patient.id)
    return render(request, 'patients/request_lab_test.html', {'patient': patient, 'available_tests': available_tests})

@login_required
def view_patient_lab_results(request, patient_id):
    patient = get_object_or_404(Patient_register, id=patient_id)
    results = LabaratoryTestResult.objects.filter(patient=patient).order_by('-test_date')
    return render(request, 'patients/patient_lab_results.html', {'patient': patient, 'results': results})


@login_required
def request_labaratory_test(request, patient_id):
    patient = get_object_or_404(Patient_register, id=patient_id)
    labaratories = Labaratory.objects.all()
    if request.method == 'POST':
        labaratory_id = request.POST.get('labaratory_id')
        test_name = request.POST.get('test_name')
        notes = request.POST.get('notes', '')
        labaratory = get_object_or_404(Labaratory, id=labaratory_id)
        # Create a lab test result as a request (Pending)
        labaratory_test = labaratory.labaratorytest_set.filter(test_name=test_name).first()
        if labaratory_test:
            LabaratoryTestResult.objects.create(
                labaratory_test=labaratory_test,
                patient=patient,
                test_result='',
                test_date=timezone.now(),
                notes=notes,
                status='Pending'
            )
        messages.success(request, f"Laboratory test '{test_name}' requested for {patient.name}.")
        return redirect('view_patient_lab_results', patient_id=patient.id)
    return render(request, 'patients/request_labaratory_test.html', {'patient': patient, 'labaratories': labaratories})




