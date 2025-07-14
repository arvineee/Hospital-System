from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from patients.models import Patient_register
from .models import Labaratory, LabaratoryTest, LabaratoryTestResult, LabaratoryAppointment, Laboratory_requests
# Create your views here.
from django.contrib.auth.decorators import login_required
from patients.views import get_active_bill_for_patient
import logging

def dashboard(request):
    if request.user.is_authenticated:
        user_role = request.user.userprofile.role
        if user_role == 'lab_tech':
            return render(request, 'labaratory/dashboard.html')
        else:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('home')
    else:
        messages.error(request, "You need to log in first.")
        return redirect('login')
def labaratory_create(request):
    if request.method == 'POST':
        labaratory_name = request.POST.get('labaratory_name')
        labaratory_location = request.POST.get('labaratory_location')
        labaratory_description = request.POST.get('labaratory_description')
        labaratory_phone = request.POST.get('labaratory_phone')
        labaratory_email = request.POST.get('labaratory_email')

        labaratory = Labaratory(
            labaratory_name=labaratory_name,
            labaratory_location=labaratory_location,
            labaratory_description=labaratory_description,
            labaratory_phone=labaratory_phone,
            labaratory_email=labaratory_email
        )
        labaratory.save()
        messages.success(request, "Laboratory created successfully.")
        return redirect('labaratory_list')
    return render(request, 'labaratory/laboratory_create.html')
def labaratory_list(request):
    labaratories = Labaratory.objects.all()
    return render(request, 'labaratory/laboratory_list.html', {'labaratories': labaratories})
def labaratory_detail(request, labaratory_id):
    labaratory = Labaratory.objects.get(id=labaratory_id)
    return render(request, 'labaratory/laboratory_detail.html', {'labaratory': labaratory})
def labaratory_test_list(request, labaratory_id):
    try:
        labaratory = get_object_or_404(Labaratory, id=labaratory_id)
        tests = LabaratoryTest.objects.filter(labaratory=labaratory)
        
        context = {
            'labaratory': labaratory,
            'tests': tests,
        }
        return render(request, 'labaratory/laboratory_test_list.html', context)
    
    except Exception as e:
        messages.error(request, f"Error retrieving tests: {str(e)}")
        return redirect('labaratory_list')
def labaratory_test_detail(request, labaratory_id, test_id):
    labaratory = Labaratory.objects.get(id=labaratory_id)
    test = LabaratoryTest.objects.get(id=test_id)
    return render(request, 'labaratory/laboratory_test_detail.html', {'labaratory': labaratory, 'test': test})
def labaratory_test_result_list(request, patient_id=None, labaratory_id=None, test_id=None):
    try:
        if patient_id:
            patient = get_object_or_404(Patient_register, id=patient_id)
            results = LabaratoryTestResult.objects.filter(patient=patient).order_by('-test_date')
            available_tests = LabaratoryTest.objects.select_related('labaratory').all()
            labaratories = Labaratory.objects.all()
            
            context = {
                'patient': patient,
                'results': results,
                'available_tests': available_tests,
                'labaratories': labaratories,
            }
            return render(request, 'labaratory/patient_test_results.html', context)
   
        else:
            # View results for a specific test
            labaratory = get_object_or_404(Labaratory, id=labaratory_id)
            test = get_object_or_404(LabaratoryTest, id=test_id, labaratory=labaratory)
            results = LabaratoryTestResult.objects.filter(labaratory_test=test)
            template = 'labaratory/laboratory_test_result_list.html'
            context = {
                'labaratory': labaratory,
                'test': test,
                'results': results,
            }
        
        return render(request, template, context)
    
    except Exception as e:
        messages.error(request, f"Error retrieving test results: {str(e)}")
        return redirect('all_patients')
def labaratory_test_result_detail(request, labaratory_id, test_id, result_id):
    labaratory = Labaratory.objects.get(id=labaratory_id)
    test = LabaratoryTest.objects.get(id=test_id)
    result = LabaratoryTestResult.objects.get(id=result_id)
    return render(request, 'labaratory/laboratory_test_results_detail.html', {'labaratory': labaratory, 'test': test, 'result': result})
def labaratory_appointment_list(request, labaratory_id):
    labaratory = Labaratory.objects.get(id=labaratory_id)
    appointments = LabaratoryAppointment.objects.filter(labaratory=labaratory)
    return render(request, 'labaratory/laboratory_appointment_list.html', {'labaratory': labaratory, 'appointments': appointments})
def labaratory_appointment_detail(request, labaratory_id, appointment_id):
    labaratory = Labaratory.objects.get(id=labaratory_id)
    appointment = LabaratoryAppointment.objects.get(id=appointment_id)
    return render(request, 'labaratory/laboratory_appointment_detail.html', {'labaratory': labaratory, 'appointment': appointment})
def labaratory_appointment_create(request, labaratory_id):
    try:
        labaratory = get_object_or_404(Labaratory, id=labaratory_id)
        patient = get_object_or_404(Patient_register, id=request.GET.get('patient_id'))
        name = patient.name
        if request.method == 'POST':
            try:
                appointment = LabaratoryAppointment(
                    labaratory=labaratory,
                    patient=patient,
                    appointment_date=request.POST.get('appointment_date'),
                    appointment_time=request.POST.get('appointment_time'),
                    appointment_reason=request.POST.get('appointment_reason'),
                    status='Pending'
                )
                appointment.save()
                messages.success(request, "Appointment scheduled successfully.")
                return redirect('labaratory_appointment_list', labaratory_id=labaratory.id)
            except Exception as e:
                messages.error(request, f"Error creating appointment: {str(e)}")
                
        context = {
            'labaratory': labaratory,
            'patient': patient,
        }
        return render(request, 'labaratory/laboratory_appointment_create.html', context)
        
    except Labaratory.DoesNotExist:
        messages.error(request, "Laboratory not found.")
        return redirect('labaratory_list')
    except Patient_register.DoesNotExist:
        messages.error(request, "Patient not found.")
        return redirect('all_patients')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('labaratory_list')
def labaratory_appointment_update(request, labaratory_id, appointment_id):
    labaratory = Labaratory.objects.get(id=labaratory_id)
    appointment = LabaratoryAppointment.objects.get(id=appointment_id)
    patient = get_object_or_404(Patient_register, id=request.GET.get('patient_id'))
    if request.method == 'POST':
        appointment.patient_name = patient
        appointment.appointment_date = request.POST['appointment_date']
        appointment.appointment_time = request.POST['appointment_time']
        appointment.appointment_reason = request.POST['appointment_reason']
        appointment.save()
        return redirect('labaratory_appointment_list', labaratory_id=labaratory.id)
    return render(request, 'labaratory/laboratory_appointment_update.html', {'labaratory': labaratory, 'appointment': appointment})
def labaratory_appointment_delete(request, labaratory_id, appointment_id):
    labaratory = Labaratory.objects.get(id=labaratory_id)
    appointment = LabaratoryAppointment.objects.get(id=appointment_id)
    if request.method == 'POST':
        appointment.delete()
        return redirect('labaratory_appointment_list', labaratory_id=labaratory.id)
    return render(request, 'labaratory/laboratory_appointment_delete.html', {'labaratory': labaratory, 'appointment': appointment})

def labaratory_test_create(request, labaratory_id):
    try:
        
        labaratory = get_object_or_404(Labaratory, id=labaratory_id)
        if request.method == 'POST':
            test_name = request.POST.get('test_name')
            test_description = request.POST.get('test_description')
            test_price = request.POST.get('test_price')
            test_duration = request.POST.get('test_duration')
            
            if not all([test_name, test_description, test_price, test_duration]):
                messages.error(request, "All fields are required.")
                return render(request, 'labaratory/laboratory_test_create.html', {'labaratory': labaratory})
            
            test = LabaratoryTest(
                labaratory=labaratory,
                test_name=test_name,
                test_description=test_description,
                test_price=test_price,
                test_duration=test_duration
            )
            test.save()
            messages.success(request, "Test created successfully.")
            return redirect('labaratory_test_list', labaratory_id=labaratory.id)
            
        return render(request, 'labaratory/laboratory_test_create.html', {'labaratory': labaratory})
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('labaratory_list')
def labaratory_test_update(request, labaratory_id, test_id):
    labaratory = Labaratory.objects.get(id=labaratory_id)
    test = LabaratoryTest.objects.get(id=test_id)
    if request.method == 'POST':
        test.test_name = request.POST['test_name']
        test.test_description = request.POST['test_description']
        test.test_price = request.POST['test_price']
        test.test_duration = request.POST['test_duration']
        test.save()
        return redirect('labaratory_test_list', labaratory_id=labaratory.id)
    return render(request, 'labaratory/laboratory_test_update.html', {'labaratory': labaratory, 'test': test})
def labaratory_test_delete(request, labaratory_id, test_id):
    labaratory = Labaratory.objects.get(id=labaratory_id)
    test = LabaratoryTest.objects.get(id=test_id)
    if request.method == 'POST':
        test.delete()
        return redirect('labaratory_test_list', labaratory_id=labaratory.id)
    return render(request, 'labaratory/labaratory_test_delete.html', {'labaratory': labaratory, 'test': test})

def patient_test_results(request, patient_id):
    try:
        patient = get_object_or_404(Patient_register, id=patient_id)
        results = LabaratoryTestResult.objects.filter(patient=patient).order_by('-test_date')
        
        context = {
            'patient': patient,
            'results': results,
        }
        return render(request, 'labaratory/patient_test_results.html', context)
    
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('pat_view', id=patient_id)
    


@login_required
def add_test_result(request, result_id): # Renamed 'test_id' to 'result_id' for clarity
    """
    Allows lab technicians to add or update results for a specific lab test request.
    This function expects to update an *existing* LabaratoryTestResult object.
    """
    result = get_object_or_404(LabaratoryTestResult, id=result_id)
    patient = result.patient # Get patient from the existing result object
    labaratory_test = result.labaratory_test # Get the test type

    if request.method == 'POST':
        try:
            test_result_text = request.POST.get('test_result', '')
            notes = request.POST.get('notes', '')
            status = request.POST.get('status', 'Completed') # Default to Completed if not provided

            # Update the result object
            result.test_result = test_result_text
            result.notes = notes
            result.status = status
            result.test_date = timezone.now() # Update test_date to completion date/time

            # Ensure the bill is assigned if it wasn't during the request phase
            # This handles edge cases where a result might be created directly without a request
            # or if the initial request didn't properly link to a bill (less likely with new logic).
            if not result.bill:
                active_bill = get_active_bill_for_patient(patient)
                if active_bill:
                    result.bill = active_bill
                    messages.info(request, "Active bill found and assigned to this lab result.")
                else:
                    messages.warning(request, "No active bill found for the patient; bill not assigned to this result.")

            # Save the updated result
            result.save() # Save all modified fields

            messages.success(request, f"Test result for {patient.name} - {labaratory_test.test_name} updated successfully.")
            return redirect('patient_test_results', patient_id=patient.id)

        except Exception as e:
            logging.logger.exception(f"Error updating test result {result_id} for patient {patient.id}: {e}")
            messages.error(request, f"Error updating test result: {str(e)}")
            return redirect('add_test_result', result_id=result.id) # Redirect back to the form on error

    context = {
        'patient': patient,
        'result': result,
        'labaratory_test': labaratory_test # Pass the test type for context in template
    }
    return render(request, 'labaratory/add_test_result.html', context) # Assuming this template exists


def labaratory_test_result_update(request, labaratory_id, test_id, result_id):
    try:
        labaratory = get_object_or_404(Labaratory, id=labaratory_id)
        test = get_object_or_404(LabaratoryTest, id=test_id, labaratory=labaratory)
        result = get_object_or_404(LabaratoryTestResult, id=result_id, labaratory_test=test)
        
        if request.method == 'POST':
            result.test_result = request.POST.get('test_result')
            result.notes = request.POST.get('notes', '')
            result.status = request.POST.get('status')
            result.save()
            
            messages.success(request, 'Test result updated successfully.')
            return redirect('patient_test_results', patient_id=result.patient.id)
        
        context = {
            'labaratory': labaratory,
            'test': test,
            'result': result,
        }
        return render(request, 'labaratory/laboratory_test_result_update.html', context)
        
    except Exception as e:
        messages.error(request, f"Error updating test result: {str(e)}")
        return redirect('patient_test_results', patient_id=result.patient.id)

def view_laboratory_requests(request,):
     requests = Laboratory_requests.objects.all()
     return render(request, 'labaratory/laboratory_requests.html', {'requests': requests})

def lab_dashboard(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    lab_results = LabaratoryTestResult.objects.all().order_by('-test_date')
    if date_from:
        lab_results = lab_results.filter(test_date__date__gte=date_from)
    if date_to:
        lab_results = lab_results.filter(test_date__date__lte=date_to)
    context = {
        'lab_results': lab_results,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'labaratory/dashboard.html', context)