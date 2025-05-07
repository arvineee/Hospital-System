from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from patients.models import Patient_register
from .models import Labaratory, LabaratoryTest, LabaratoryTestResult, LabaratoryAppointment
# Create your views here.
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
    


def add_test_result(request, test_id, patient_id):
    test = get_object_or_404(LabaratoryTest, id=test_id)
    patient = get_object_or_404(Patient_register, id=patient_id)
    
    if request.method == 'POST':
        try:
            result = LabaratoryTestResult(
                labaratory_test=test,
                patient=patient,
                test_result=request.POST.get('test_result'),
                notes=request.POST.get('notes', '')
            )
            result.save()
            messages.success(request, 'Test result added successfully.')
            return redirect('patient_test_results', patient_id=patient.id)
        except Exception as e:
            messages.error(request, f'Error adding test result: {str(e)}')
    
    context = {
        'test': test,
        'patient': patient,
    }
    return render(request, 'labaratory/add_test_result.html', context)

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
