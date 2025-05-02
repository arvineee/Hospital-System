from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import Patient_register, PatientHistory
from drugs.models import DrugIssue
from django.contrib.auth.decorators import login_required
from drugs.models import Drug, DrugIssue 
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from labaratory.models import Labaratory
from labaratory.models import LabaratoryTestResult

from datetime import datetime


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
    return render(request, 'patients/view.html', {
        'patient': patient,
        'labaratories': labaratories
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
        
        # Clear previous drug issues for this patient
        DrugIssue.objects.filter(patient=patient).delete()
        
        patient.save()
        
        messages.success(request, "Patient successfully re-admitted.")
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

        # Check if patient is already discharged
        if patient.is_discharged:
            messages.error(request, "Patient is already discharged and billed.")
            return redirect('pat_view', id=id)

        # Calculate billing period
        admission_date = patient.adm_date
        current_date = datetime.now().date()
        days_admitted = (current_date - admission_date).days or 1  # Minimum 1 day

        # Define charges
        consultation_charge = 500
        daily_room_charge = 100
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

        # Calculate total bill
        total_bill = {
            'consultation_charge': consultation_charge,
            'room_charge': total_room_charge,
            'medication_charge': medication_total,
            'laboratory_charge': laboratory_total,
            'days_admitted': days_admitted,
            'daily_room_rate': daily_room_charge,
            'total': consultation_charge + total_room_charge + medication_total + laboratory_total
        }

        context = {
            'patient': patient,
            'drug_issues': drug_issues,
            'lab_results': lab_results,
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
        drugs = Drug.objects.all()
        history = PatientHistory.objects.filter(patient=patient).order_by('-date')

        if request.method == 'POST':
            # Retrieve form data
            diagnosis = request.POST.get('diagnosis')
            notes = request.POST.get('notes')
            doctor = request.user
            # Validate required fields
            if not all([diagnosis, notes, doctor]):
                messages.error(request, "Diagnosis, notes, and doctor name are required.")
                return render(request, 'patients/patient_history.html', {
                    'patient': patient,
                    'history': history,
                    'doctor': doctor,
                })

            try:
                # Create a new history record
                history_entry = PatientHistory(
                    patient=patient,
                    diagnosis=diagnosis,
                    notes=notes,
                    doctor=doctor
                )

                history_entry.save()
                messages.success(request, "Patient history successfully updated.")
                return redirect('patient_history', id=id)

            except Exception as e:
                messages.error(request, f"Error saving history: {str(e)}")
                return render(request, 'patients/patient_history.html', {
                    'patient': patient,
                    'history': history,
                    'doctor': doctor,
                })

        # GET request - display history
        return render(request, 'patients/patient_history.html', {
            'patient': patient,
            'history': history,
        })

    except Patient_register.DoesNotExist:
        messages.error(request, "Patient not found.")
        return redirect('all_patients')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('all_patients')