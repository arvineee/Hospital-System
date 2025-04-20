from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import Patient_register

# Create your views here.
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
            messages.error("Patient with this name and contact already exists.")
            return render(request, 'patients/register.html')

        # Create and save the new patient
        new_patient = Patient_register(name=name, age=age, contact=contact, sex=sex)
        new_patient.save()

        # Redirect or return success response
        messages.success(request, "Patient successfully registered.")
        return HttpResponse("Patient succeffuly registered")  # Replace 'success_page' with your actual success URL

    # If GET request, render the registration form
    return render(request, 'patients/register.html')  # Replace with your actual template path