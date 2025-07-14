from django.contrib.admin.views.decorators import staff_member_required
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
from django.views.decorators.http import require_GET, require_http_methods
from django.shortcuts import get_object_or_404
from labaratory.models import Labaratory
from labaratory.models import LabaratoryTestResult, LabaratoryTest
from radiology.models import Ultrasound
from django.utils import timezone
from datetime import datetime,timedelta
from django.db.models import Q 
import logging
from radiology.models import UltrasoundRequest
from reportlab.platypus import Paragraph, Table, TableStyle, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from django.core.mail import EmailMultiAlternatives
from decimal import Decimal
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Table, TableStyle, SimpleDocTemplate, Spacer
from reportlab.lib.units import cm
import base64
from django.http import HttpResponse
from django.core.files.base import ContentFile
from drugs.models import Drug, DrugIssue # Ensure DrugIssue is imported
from labaratory.models import Labaratory, LabaratoryTestResult # Ensure LabaratoryTestResult is imported
from radiology.models import Ultrasound, UltrasoundRequest # Ensure Ultrasound is imported
from django.db import transaction
import json
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from reportlab.platypus import Paragraph, Table, TableStyle, SimpleDocTemplate, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Image as ReportLabImage # Renamed to avoid conflict
import os # For path joining, if using local images
import base64


logger = logging.getLogger(__name__)



# helper to get active bill
def get_active_bill_for_patient(patient):
    """
    Retrieves the patient's currently active (unpaid and not overdue/carried over) bill.
    If multiple, returns the most recent one.
    """
    # A bill is considered 'active' for new charges if it's not paid
    # and its balance has not been carried over to a new admission (is_overdue=False).
    active_bill = Billing.objects.filter(
        patient=patient,
        is_paid=False,
        is_overdue=False  # Crucial to exclude bills whose balance was transferred
    ).order_by('-created_at').first()
    return active_bill


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



@login_required
@require_http_methods(["GET", "POST"])
def update_payment(request, bill_id):
    bill = get_object_or_404(Billing, id=bill_id)
    patient = bill.patient
    if request.method == "POST":
        try:
            paid_amount = Decimal(request.POST.get("paid_amount", 0))
            payment_method = request.POST.get("payment_method", "")
            payment_reference = request.POST.get("payment_reference", "")

            if paid_amount < 0 or paid_amount > bill.total_amount:
                messages.error(request, "Invalid payment amount.")
                return render(request, "patients/update_payment.html", {"bill": bill, "patient": patient})

            PaymentHistory.objects.create(
                bill=bill,
                paid_amount=paid_amount,
                payment_method=payment_method,
                payment_reference=payment_reference,
                paid_by=request.user
            )

            bill.paid_amount += paid_amount
            bill.due_amount = bill.total_amount - bill.paid_amount
            bill.payment_method = payment_method
            bill.payment_reference = payment_reference
            bill.updated_at = timezone.now()
            bill.update_status()

            if bill.due_amount <= 0:
                bill.is_paid = True
                bill.due_amount = 0

            bill.save(update_fields=["paid_amount", "due_amount", "payment_method", "payment_reference", "updated_at", "is_paid", "status"])

            try:
                Hospital_name = getattr(settings, 'HOSPITAL_NAME', 'HMS Hospital System')
                subject = f"[{Hospital_name}] Payment Received for {patient.name} (Bill #{bill.id})"
                text_message = f"Payment made for {patient.name}, Bill #{bill.id}, Amount: {paid_amount}"
                html_message = f"<p>Payment received for patient <strong>{patient.name}</strong>. Amount: Ksh {paid_amount}</p>"

                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A5)
                styles = getSampleStyleSheet()
                elements = [
                    Paragraph("Payment Receipt", styles['Title']),
                    Spacer(1, 12),
                    Table([
                        ["Patient Name", patient.name],
                        ["Patient ID", patient.id],
                        ["Bill ID", bill.id],
                        ["Amount Paid", f"Ksh {paid_amount}"],
                        ["Payment Method", payment_method],
                        ["Payment Reference", payment_reference],
                        ["Paid By", request.user.get_full_name() or request.user.username],
                        ["Bill Status", bill.status],
                        ["Total", f"Ksh {bill.total_amount}"],
                        ["Paid", f"Ksh {bill.paid_amount}"],
                        ["Due", f"Ksh {bill.due_amount}"],
                    ], style=TableStyle([
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ]))
                ]
                doc.build(elements)
                pdf_data = buffer.getvalue()
                buffer.close()

                pdf_filename = f"receipt_bill_{bill.id}.pdf"
                # Correct way to save binary data to BinaryField
                bill.receipt_pdf = pdf_data
                bill.save(update_fields=['receipt_pdf'])
                bill.refresh_from_db()

                request.session['last_receipt_pdf'] = base64.b64encode(pdf_data).decode('utf-8')
                print("PDF session stored with size:", len(pdf_data))

                admins = getattr(settings, 'ADMINS', [('Admin', 'admin@example.com')])
                admin_emails = [email for _, email in admins if email]
                msg = EmailMultiAlternatives(subject, text_message, settings.DEFAULT_FROM_EMAIL, admin_emails)
                msg.attach_alternative(html_message, "text/html")

                msg.attach(pdf_filename, pdf_data, "application/pdf")

                msg.send(fail_silently=False)
                print("Email sent to:", admin_emails)

            except Exception as exc:
                print(f"Payment notification error: {exc}")

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
    payment_history = bill.payment_history.order_by('-timestamp')
    return render(request, "patients/update_payment.html", {"bill": bill, "patient": patient, "payment_history": payment_history})

@require_GET
def download_receipt(request, bill_id):
    pdf_data = None
    pdf_b64 = request.session.get('last_receipt_pdf')
    if pdf_b64:
        try:
            pdf_data = base64.b64decode(pdf_b64)
            print("PDF loaded from session")
        except Exception as e:
            print(f"Base64 decode error: {e}")
    if not pdf_data:
        bill = Billing.objects.filter(id=bill_id).first()
        if bill and bill.receipt_pdf:
            # For BinaryField, the data is already directly in bill.receipt_pdf
            pdf_data = bill.receipt_pdf
            print("PDF loaded from model field")
        else:
            print("Receipt PDF not found on model")
            return HttpResponse('No receipt available.', status=404)
    if not pdf_data:
        return HttpResponse('No receipt data found.', status=404)
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_bill_{bill_id}.pdf"'
    return response
@login_required
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
            residence =request.POST.get('residence')

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
                residence=residence,
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
        
# In patients/views.py

@login_required
def discharge_patient(request, patient_id):
    patient = get_object_or_404(Patient_register, id=patient_id)

    if request.method == 'POST':
        discharge_date_str = request.POST.get('discharge_date')
        discharge_notes = request.POST.get('discharge_notes')
        condition_at_discharge = request.POST.get('condition_at_discharge')
        follow_up_instructions = request.POST.get('follow_up_instructions')
        medications_at_discharge = request.POST.get('medications_at_discharge')

        # Convert date string to date object
        try:
            discharge_date = datetime.strptime(discharge_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid discharge date format.")
            return render(request, 'patients/discharge.html', {'patient': patient})

        # Update patient status and discharge summary details
        patient.is_discharged = True
        patient.discharge_date = discharge_date
        patient.status = 'Discharged'
        patient.discharge_doctor = request.user # Set the discharging doctor to the logged-in user
        patient.discharge_notes = discharge_notes
        patient.condition_at_discharge = condition_at_discharge
        patient.follow_up_instructions = follow_up_instructions
        patient.medications_at_discharge = medications_at_discharge

        patient.save()

        messages.success(request, f'Patient {patient.name} has been successfully discharged and summary recorded.')
        # Redirect to the PDF generation view
        return redirect('generate_discharge_summary_pdf', patient_id=patient.id)

    return render(request, 'patients/discharge.html', {'patient': patient})


# Helper function to get or create a ParagraphStyle
def get_or_create_style(styles, name, **kwargs):
    if name not in styles:
        styles.add(ParagraphStyle(name=name, **kwargs))
    return styles[name]

@login_required
def generate_discharge_summary_pdf(request, patient_id):
    patient = get_object_or_404(Patient_register, id=patient_id)
    discharge_date = patient.discharge_date if patient.discharge_date else timezone.now().date()
    patient_history = PatientHistory.objects.filter(patient=patient).order_by('date')
    lab_results = LabaratoryTestResult.objects.filter(patient=patient).order_by('test_date')
    issued_drugs = DrugIssue.objects.filter(patient=patient).order_by('issue_date')
    patient_bill = Billing.objects.filter(patient=patient).first()
    ultrasound_results = Ultrasound.objects.filter(patient=patient).order_by('date')


    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A5,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()

    # Define custom styles or get existing ones
    h1_style = get_or_create_style(styles, 'h1', fontSize=14, leading=16, alignment=TA_CENTER, fontName='Helvetica-Bold')
    h2_style = get_or_create_style(styles, 'h2', fontSize=12, leading=14, alignment=TA_LEFT, fontName='Helvetica-Bold')
    body_style = get_or_create_style(styles, 'BodyText', fontSize=10, leading=12, alignment=TA_LEFT, fontName='Helvetica')
    right_align_style = get_or_create_style(styles, 'RightAlign', fontSize=10, leading=12, alignment=TA_RIGHT, fontName='Helvetica')
    center_align_style = get_or_create_style(styles, 'CenterAlign', fontSize=10, leading=12, alignment=TA_CENTER, fontName='Helvetica')
    table_header_style = get_or_create_style(styles, 'TableHeader', fontSize=10, leading=12, alignment=TA_CENTER, fontName='Helvetica-Bold',
                                           backColor=colors.lightgrey)

    elements = []

    # Hospital Header
    elements.append(Paragraph(settings.HOSPITAL_NAME, h1_style))
    elements.append(Paragraph("Discharge Summary", h1_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Patient Information
    elements.append(Paragraph("<b>Patient Information:</b>", h2_style))
    elements.append(Paragraph(f"<b>Name:</b> {patient.name}", body_style))
    elements.append(Paragraph(f"<b>Age:</b> {patient.age}", body_style))
    elements.append(Paragraph(f"<b>Sex:</b> {patient.sex}", body_style))
    elements.append(Paragraph(f"<b>Admission Date:</b> {patient.adm_date.strftime('%Y-%m-%d')}", body_style))
    elements.append(Paragraph(f"<b>Discharge Date:</b> {discharge_date.strftime('%Y-%m-%d')}", body_style))
    elements.append(Paragraph(f"<b>Status at Discharge:</b> {patient.status}", body_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Patient History
    elements.append(Paragraph("<b>Patient History:</b>", h2_style))
    if patient_history:
        history_data = [['Date', 'Signs', 'Symptoms', 'Temperature', 'Diagnosis']]
        for entry in patient_history:
            history_data.append([
                entry.date.strftime('%Y-%m-%d'),
                entry.signs,
                entry.symptoms,
                str(entry.temperature),
                entry.diagnosis
            ])
        history_table = Table(history_data, colWidths=[1.8*cm, 2.5*cm, 2.5*cm, 2*cm, 3.5*cm])
        history_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8), # Smaller font for table content
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(history_table)
    else:
        elements.append(Paragraph("No patient history recorded.", body_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Lab Results
    elements.append(Paragraph("<b>Laboratory Results:</b>", h2_style))
    if lab_results:
        lab_data = [['Test Name', 'Result', 'Date', 'Status']]
        for result in lab_results:
            lab_data.append([
                result.labaratory_test.test_name if result.labaratory_test else 'N/A',
                result.test_result,
                result.test_date.strftime('%Y-%m-%d'),
                result.status
            ])
        lab_table = Table(lab_data, colWidths=[3*cm, 4*cm, 2*cm, 2*cm])
        lab_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(lab_table)
    else:
        elements.append(Paragraph("No laboratory results found.", body_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Issued Drugs
    elements.append(Paragraph("<b>Issued Medications:</b>", h2_style))
    if issued_drugs:
        drug_data = [['Drug Name', 'Quantity', 'Issue Date']]
        for issue in issued_drugs:
            drug_data.append([
                issue.drug.name,
                str(issue.quantity_issued),
                issue.issue_date.strftime('%Y-%m-%d')
            ])
        drug_table = Table(drug_data, colWidths=[4*cm, 2*cm, 3*cm])
        drug_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(drug_table)
    else:
        elements.append(Paragraph("No medications issued.", body_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Ultrasound Results
    elements.append(Paragraph("<b>Ultrasound Results:</b>", h2_style))
    if ultrasound_results:
        us_data = [['Type', 'Findings', 'Date']]
        for us in ultrasound_results:
            us_data.append([
                us.ultrasound_type,
                us.findings if us.findings else 'N/A',
                us.date.strftime('%Y-%m-%d')
            ])
        us_table = Table(us_data, colWidths=[3*cm, 5*cm, 2*cm])
        us_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(us_table)
    else:
        elements.append(Paragraph("No ultrasound results found.", body_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Billing Information
    elements.append(Paragraph("<b>Billing Summary:</b>", h2_style))
    if patient_bill:
        elements.append(Paragraph(f"<b>Total Amount:</b> Ksh {patient_bill.total_amount}", body_style))
        elements.append(Paragraph(f"<b>Amount Paid:</b> Ksh {patient_bill.paid_amount}", body_style))
        elements.append(Paragraph(f"<b>Due Amount:</b> Ksh {patient_bill.due_amount}", body_style))
        elements.append(Paragraph(f"<b>Bill Status:</b> {patient_bill.status}", body_style))

        if patient_bill.details:
            elements.append(Paragraph("<b>Detailed Charges:</b>", body_style))
            for key, value in patient_bill.details.items():
                # Format the key for display (e.g., "medication_charge" -> "Medication Charge")
                display_key = key.replace('_', ' ').title()
                elements.append(Paragraph(f"  <b>{display_key}:</b> Ksh {value}", body_style))
    else:
        elements.append(Paragraph("No billing information found.", body_style))
    elements.append(Spacer(1, 1 * cm))

    # Footer
    elements.append(Paragraph(f"<i>Summary generated by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}</i>", center_align_style))

    try:
        doc.build(elements)
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf')
    except Exception as e:
        logger.error(f"Error generating PDF for patient {patient_id}: {e}")
        messages.error(request, f"Error generating PDF: {e}")
        return redirect('patient_detail', patient_id=patient_id)


@login_required
def re_admit(request, id):
    try:
        patient = get_object_or_404(Patient_register, id=id)

        # Check if patient is already admitted
        if not patient.is_discharged:
            messages.error(request, "Patient is already admitted. Cannot re-admit.")
            return redirect('all_patients')

        # Use a transaction for atomic operations
        with transaction.atomic():
            # Process previous pending bills
            previous_pending_bills = Billing.objects.filter(
                patient=patient,
                is_paid=False,
                is_overdue=False  # Only consider bills not yet marked as overdue
            ).order_by('created_at')

            total_previous_due = Decimal('0.00')

            if previous_pending_bills.exists():
                for prev_bill in previous_pending_bills:
                    total_previous_due += prev_bill.due_amount
                    prev_bill.is_overdue = True
                    prev_bill.status = 'overdue_carried'  # Mark as carried over
                    prev_bill.save(update_fields=['is_overdue', 'status'])
                messages.warning(request, f"Previous unpaid bill(s) totaling KSH {total_previous_due:.2f} identified and marked as carried over.")

            # --- Important: Collect ALL currently unbilled items for this patient ---
            # These items, if they exist, are from a previous admission period that were never assigned a bill.
            # They should be associated with the new bill created on re-admission.
            unbilled_drug_issues = list(DrugIssue.objects.filter(patient=patient, bill__isnull=True))
            unbilled_lab_results = list(LabaratoryTestResult.objects.filter(patient=patient, bill__isnull=True))
            unbilled_ultrasounds = list(Ultrasound.objects.filter(patient=patient, bill__isnull=True))

            # Update patient's admission status and date for re-admission
            patient.is_discharged = False
            patient.discharge_date = None
            patient.adm_date = datetime.now()  # Set new admission date/time
            patient.save(update_fields=['is_discharged', 'discharge_date', 'adm_date'])

            # Create a new bill for the re-admitted patient
            # This bill will carry forward the total_previous_due
            details_for_new_bill = {
                'previous_pending_due': float(total_previous_due),
                'note': 'New admission. Includes previous unpaid bill(s) due.',
                'amount_paid_to_date': 0.0,
            }

            new_bill = Billing.objects.create(
                patient=patient,
                total_amount=Decimal('0.00'),  # This will be updated by the 'billing' function later
                paid_amount=Decimal('0.00'),
                due_amount=total_previous_due,  # Initial due is just the carried over amount
                is_paid=False,
                details=details_for_new_bill,
                generated_by=request.user if request.user.is_authenticated else None,
                status='unpaid',  # Status on creation. Can be 'pending' if no previous due.
                is_overdue=(total_previous_due > 0)  # Mark as overdue if there was a previous due
            )

            # --- Now, link the collected unbilled items to the newly created bill ---
            for issue in unbilled_drug_issues:
                issue.bill = new_bill
                issue.save(update_fields=['bill'])

            for result in unbilled_lab_results:
                result.bill = new_bill
                result.save(update_fields=['bill'])

            for us in unbilled_ultrasounds:
                us.bill = new_bill
                us.save(update_fields=['bill'])

            if total_previous_due > 0:
                messages.success(request, f"Patient successfully re-admitted. Previous unpaid bill(s) of KSH {total_previous_due:.2f} carried forward to new bill.")
            else:
                messages.success(request, "Patient successfully re-admitted. All previous bills were cleared. New bill started.")

        return redirect('pat_view', id=id)  # Use patient_id directly as it's passed

    except Patient_register.DoesNotExist:
        messages.error(request, "Patient not found.")
        logger.error(f"Patient with ID {id} not found in re_admit view.")
        return redirect('all_patients')
    except Exception as e:
        messages.error(request, f"An unexpected error occurred during re-admission: {str(e)}")
        logger.exception(f"Error in re_admit view for patient ID {id}: {e}")
        return redirect('all_patients')
@login_required
def billing(request, id):
    try:
        patient = get_object_or_404(Patient_register, id=id)

        adm_datetime = patient.adm_date

        # --- Fetch only UNBILLED items for the patient ---
        drug_issues_to_bill = DrugIssue.objects.filter(
            patient=patient,
            issue_date__gte=adm_datetime,
            bill__isnull=True # Only unbilled drug issues
        ).order_by('issue_date')

        lab_results_to_bill = LabaratoryTestResult.objects.filter(
            patient=patient,
            test_date__gte=adm_datetime,
            bill__isnull=True # Only unbilled lab results
        ).order_by('test_date')

        # --- UPDATED: Filtering Ultrasound by ForeignKey to Patient_register ---
        ultrasounds_to_bill = Ultrasound.objects.filter(
            patient=patient, # Now filtering directly by the Patient_register object
            created_at__gte=adm_datetime,
            bill__isnull=True # Only unbilled ultrasounds
        ).order_by('-created_at')

        # Calculate billing period (days admitted)
        admission_date_only = adm_datetime.date() if isinstance(adm_datetime, datetime) else adm_datetime
        current_date = timezone.now().date()
        days_admitted = (current_date - admission_date_only).days
        if days_admitted < 1:
            days_admitted = 1

        # --- Calculate Charges (using Decimal for accuracy) ---
        consultation_charge = Decimal('100.00')
        daily_room_charge = Decimal('0.00') # This is currently hardcoded to 0.00
        total_room_charge = daily_room_charge * Decimal(days_admitted)

        medication_total = sum(Decimal(str(issue.drug.price)) * issue.quantity_issued for issue in drug_issues_to_bill)
        laboratory_total = sum(Decimal(str(result.labaratory_test.test_price)) for result in lab_results_to_bill if result.labaratory_test)
        ultrasound_total = sum(Decimal(str(us.price)) for us in ultrasounds_to_bill)

        current_period_total = consultation_charge + total_room_charge + medication_total + laboratory_total + ultrasound_total

        # --- Handle previous pending due amounts ---
        bill_obj = Billing.objects.filter(
            patient=patient,
            is_paid=False,
        ).order_by('-created_at').first()

        previous_pending_due = Decimal('0.00')
        note_for_previous_due = ""

        if bill_obj and bill_obj.details and bill_obj.details.get('previous_pending_due'):
            temp_previous_due = Decimal(str(bill_obj.details['previous_pending_due']))
            if temp_previous_due > 0:
                previous_pending_due = temp_previous_due
                note_for_previous_due = bill_obj.details.get('note', 'Includes previous unpaid bill(s) due on re-admission.')

        total_with_pending = current_period_total + previous_pending_due

        # Prepare details for Billing model (JSONField)
        details = {
            'consultation_charge': float(consultation_charge),
            'room_charge': float(total_room_charge),
            'medication_charge': float(medication_total),
            'laboratory_charge': float(laboratory_total),
            'ultrasound_charge': float(ultrasound_total),
            'days_admitted': days_admitted,
            'daily_room_rate': float(daily_room_charge),
            'billing_period_start': admission_date_only.isoformat(),
            'billing_period_end': current_date.isoformat(),
            'current_period_total': float(current_period_total),
        }
        if previous_pending_due > 0:
            details['previous_pending_due'] = float(previous_pending_due)
            details['note'] = note_for_previous_due

        bill_changed = False
        with transaction.atomic():
            if bill_obj:
                current_details_json = json.dumps(details, sort_keys=True)
                bill_obj_details_json = json.dumps(bill_obj.details, sort_keys=True)

                if bill_obj.total_amount != total_with_pending or current_details_json != bill_obj_details_json:
                    bill_obj.total_amount = total_with_pending
                    bill_obj.details = details
                    bill_obj.due_amount = max(Decimal('0.00'), total_with_pending - bill_obj.paid_amount)
                    bill_obj.is_paid = bill_obj.due_amount <= Decimal('0.00')
                    bill_obj.save(update_fields=["total_amount", "due_amount", "details", "is_paid"])
                    bill_changed = True
                    messages.info(request, "Existing bill updated with latest charges.")
            else:
                bill_obj = Billing.objects.create(
                    patient=patient,
                    total_amount=total_with_pending,
                    paid_amount=Decimal('0.00'),
                    due_amount=total_with_pending,
                    is_paid=False,
                    details=details,
                    generated_by=request.user if request.user.is_authenticated else None,
                )
                bill_changed = True
                messages.success(request, "New bill generated for the patient.")

            if bill_changed:
                for item_list in [drug_issues_to_bill, lab_results_to_bill, ultrasounds_to_bill]:
                    for item in item_list:
                        item.bill = bill_obj
                        item.save(update_fields=['bill'])

        # Prepare context for template
        all_patient_bills = Billing.objects.filter(patient=patient).order_by('-created_at')
        payment_history = PaymentHistory.objects.filter(bill=bill_obj).order_by('-timestamp')

        if bill_obj.is_paid and bill_obj.due_amount <= 0 and not bill_changed:
            messages.success(request, "This bill is fully paid. No outstanding charges remain.")
            return redirect('pat_view', id=patient.id)

        context = {
            'patient': patient,
            'drug_issues': drug_issues_to_bill,
            'lab_results': lab_results_to_bill,
            'ultrasounds': ultrasounds_to_bill,
            'bill': bill_obj,
            'all_patient_bills': all_patient_bills,
            'admission_date': admission_date_only,
            'current_date': current_date,
            'payment_history': payment_history,
        }

        receipt_pdf = request.session.pop('last_receipt_pdf', None)
        if receipt_pdf:
            context['receipt_pdf'] = receipt_pdf

        return render(request, 'patients/billing.html', context)

    except Patient_register.DoesNotExist:
        messages.error(request, "Patient not found.")
        logger.error(f"Patient with ID {id} not found in billing view.")
        return redirect('all_patients')
    except Exception as e:
        messages.error(request, f"An unexpected error occurred during billing: {str(e)}")
        logger.exception(f"Error in billing view for patient ID {id}: {e}")
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
    """
    Handles requesting a lab test for a patient.
    Links the requested test result to the patient's active bill and updates the bill's laboratory charge.
    """
    patient = get_object_or_404(Patient_register, id=patient_id)
    labaratories = Labaratory.objects.all() # Get all labs to allow selection

    if request.method == 'POST':
        labaratory_id = request.POST.get('labaratory_id')
        # Assuming you're selecting a LabaratoryTest by ID from a dropdown, not by name string
        labaratory_test_id = request.POST.get('labaratory_test_id')
        notes = request.POST.get('notes', '')

        # Input validation
        if not labaratory_id or not labaratory_test_id:
            messages.error(request, "Please select a laboratory and a test.")
            context = {'patient': patient, 'labaratories': labaratories}
            return render(request, 'labaratory/request_labaratory_test.html', context)

        try:
            # Retrieve the specific LabaratoryTest object
            labaratory_test = get_object_or_404(LabaratoryTest, id=labaratory_test_id, labaratory_id=labaratory_id)
        except LabaratoryTest.DoesNotExist:
            messages.error(request, "Invalid laboratory test selected.")
            context = {'patient': patient, 'labaratories': labaratories}
            return render(request, 'labaratory/request_labaratory_test.html', context)
        except Exception as e:
            messages.error(request, f"An unexpected error occurred during test selection: {e}")
            context = {'patient': patient, 'labaratories': labaratories}
            return render(request, 'labaratory/request_labaratory_test.html', context)


        # Get the patient's active bill
        active_bill = get_active_bill_for_patient(patient)
        if not active_bill:
            messages.error(request, "No active bill found for this patient. Cannot request lab test without an active bill. Please create a bill or re-admit the patient.")
            return redirect('pat_view', id=patient.id) # Use id consistent with patient view URL

        try:
            with transaction.atomic():
                # Create a LabaratoryTestResult object as a request (status='Pending')
                LabaratoryTestResult.objects.create(
                    labaratory_test=labaratory_test,
                    patient=patient,
                    test_result='',  # Empty result initially
                    test_date=timezone.now(),
                    notes=notes,
                    status='Pending', # Status for pending request
                    bill=active_bill # Assign the active bill here
                )

                # Update the active bill's laboratory_charge
                if not active_bill.details:
                    active_bill.details = {} # Ensure 'details' dictionary exists

                current_lab_charge = Decimal(str(active_bill.details.get('laboratory_charge', 0.0)))
                test_cost = labaratory_test.test_price
                active_bill.details['laboratory_charge'] = float(current_lab_charge + test_cost)

                # Recalculate total_amount and due_amount for the bill
                active_bill.total_amount = Decimal(str(active_bill.total_amount)) + test_cost
                active_bill.due_amount = Decimal(str(active_bill.due_amount)) + test_cost # Assuming no payment applied yet

                active_bill.save(update_fields=['details', 'total_amount', 'due_amount'])

            messages.success(request, f'Lab test "{labaratory_test.test_name}" requested successfully for {patient.name} and bill updated.')
            return redirect('patient_test_results', patient_id=patient.id) # Redirect to patient's lab results page

        except Exception as e:
            logger.exception(f"Error requesting lab test or updating bill for patient {patient.id}: {e}")
            messages.error(request, f"An error occurred while requesting lab test and updating bill: {e}")
            return redirect('request_labaratory_test', patient_id=patient.id)


    context = {
        'patient': patient,
        'labaratories': labaratories,
    }
    return render(request, 'labaratory/request_labaratory_test.html', context)
