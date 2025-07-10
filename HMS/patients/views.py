from django.shortcuts import render, redirect
from django.http import HttpResponse
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

# Create your views here.
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
        
        # Update the patient's re-admission status
        patient.is_discharged = False
        patient.discharge_date = None
        patient.adm_date = datetime.now().date()
        
        # Do NOT clear previous records. All previous drug issues, lab results, and ultrasounds are kept.
        patient.save()

        messages.success(request, "Patient successfully re-admitted. Previous records have been kept.")
        return redirect('pat_view', id=id)  # Redirect to the patient's view page
    
    except Patient_register.DoesNotExist:
        messages.error(request, "Patient not found.")
        return redirect('all_patients')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('all_patients')

def billing(request, id):
    try:
        patient = get_object_or_404(Patient_register, id=id)
        drug_issues = DrugIssue.objects.filter(patient=patient)
        lab_results = LabaratoryTestResult.objects.filter(patient=patient)
        # Only include ultrasounds for this admission (on or after adm_date)
        ultrasounds = Ultrasound.objects.filter(patient=patient.name, date__gte=patient.adm_date)

        # Check if patient is already discharged
        if patient.is_discharged:
            messages.error(request, "Patient is already discharged and billed.")
            return redirect('pat_view', id=id)

        # Calculate billing period
        admission_date = patient.adm_date
        current_date = datetime.now().date()
        days_admitted = (current_date - admission_date).days or 1  # Minimum 1 day

        # Define charges
        consultation_charge = 100
        daily_room_charge = 0
        total_room_charge = daily_room_charge * days_admitted

        # Calculate medication charges
        medication_total = sum(
            issue.drug.price * issue.quantity_issued 
            for issue in drug_issues
        )

        # Calculate laboratory charges
        laboratory_total = sum(
            result.labaratory_test.test_price
            for result in lab_results
        )

        # Calculate ultrasound charges
        ultrasound_total = sum(
            us.price for us in ultrasounds
        )

        # Calculate total bill
        total_bill = {
            'consultation_charge': consultation_charge,
            'room_charge': total_room_charge,
            'medication_charge': medication_total,
            'laboratory_charge': laboratory_total,
            'ultrasound_charge': ultrasound_total,
            'days_admitted': days_admitted,
            'daily_room_rate': daily_room_charge,
            'total': consultation_charge + total_room_charge + medication_total + laboratory_total + ultrasound_total
        }

        context = {
            'patient': patient,
            'drug_issues': drug_issues,
            'lab_results': lab_results,
            'ultrasounds': ultrasounds,
            'bill': total_bill,
            'admission_date': admission_date,
            'current_date': current_date,
        }

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




