from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import Patient_register
from drugs.models import Drug, DrugIssue 

# Create your views here.
def all_patients(request):
    patients = Patient_register.objects.all()
    return render(request, 'patients/home.html', {'patients': patients})
def pat_register(request):
    if request.method == 'POST':
        # Retrieve form data
        name = request.POST.get('name')
        age = request.POST.get('age')
        contact = request.POST.get('contact')
        sex = request.POST.get('sex')

        # Validate required fields
        if not all([name, age, contact, sex]):
            messages.error(request,"All fields are required.")
            return render(request, 'patients/register.html')

        # Check for duplicate patient
        if Patient_register.objects.filter(name=name, contact=contact).exists():
            messages.error(request,"Patient with this name and contact already exists.")
            return render(request, 'patients/register.html')

        # Create and save the new patient
        new_patient = Patient_register(name=name, age=age, contact=contact, sex=sex)
        new_patient.save()

        # Redirect or return success response
        messages.success(request, "Patient successfully registered.")
        return redirect(all_patients)  # Replace 'success_page' with your actual success URL

    # If GET request, render the registration form
    return render(request, 'patients/register.html')  # Replace with your actual template path

def pat_update(request, id):
    patient = Patient_register.objects.get(id=id)
    if request.method == 'POST':
        # Retrieve form data
        name = request.POST.get('name')
        age = request.POST.get('age')
        contact = request.POST.get('contact')
        sex = request.POST.get('sex')
        # Validate required fields
        if not all([name, age, contact,sex]):
            messages.error(request,"All fields are required.")
            return render(request, 'patients/update.html', {'patient': patient})
        # Check for duplicate patient
        if Patient_register.objects.filter(name=name, contact=contact).exclude(id=id).exists():
            messages.error(request,"Patient with this name and contact already exists.")
            return render(request, 'patients/update.html', {'patient': patient})
        # Update the patient details
        patient.name = name
        patient.age = age
        patient.contact = contact 
        patient.sex = sex   
        patient.save()
        # Redirect or return success response
        messages.success(request, "Patient details successfully updated.")
        return redirect(all_patients)
    # If GET request, render the update form with existing patient data
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
def pat_search(request, name=None):
    if name:
        # Perform a case-insensitive search and strip extra spaces
        patients = Patient_register.objects.filter(name__iexact=name.strip())
        if patients.exists():
            return render(request, 'patients/search_results.html', {'patients': patients})
        else:
            messages.error(request, "No patient found with the given name.")
            return redirect(all_patients)
    
def pat_view(request, id):
    patient = Patient_register.objects.get(id=id)
    return render(request, 'patients/view.html', {'patient': patient}) 


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
        return redirect(all_patients)  

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