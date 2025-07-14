from django.shortcuts import render, get_object_or_404, redirect
from .models import Ultrasound, UltrasoundRequest
from patients.models import Patient_register
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from patients.views import get_active_bill_for_patient
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)
# Create your views here.

def ultrasound_list(request):
    ultrasounds = Ultrasound.objects.all()
    context = {
        'ultrasounds': ultrasounds
    }
    return render(request, 'radiology/ultrasound_list.html', context)


@login_required
def ultrasound_create(request, patient_id=None):
    """
    Allows creating a new ultrasound record for a patient.
    Can be initiated with a pre-selected patient or by selecting one from a list.
    Links the ultrasound to the patient's active bill and updates the bill's ultrasound charge.
    """
    patient = None
    patients = Patient_register.objects.all() # For dropdown if patient_id is not provided

    if patient_id:
        patient = get_object_or_404(Patient_register, id=patient_id)

    # Initialize active_bill based on the patient (if known)
    active_bill = None
    if patient:
        active_bill = get_active_bill_for_patient(patient)
        if not active_bill:
            messages.error(request, "No active bill found for this patient. Cannot create ultrasound record. Please create a bill or re-admit the patient.")
            return redirect('pat_view', id=patient.id) # Use id consistent with patient view URL

    if request.method == 'POST':
        selected_patient_id = request.POST.get('patient_id') # Get patient from form
        ultrasound_type = request.POST.get('ultrasound_type')
        findings = request.POST.get('findings', '')
        image = request.FILES.get('image')

        # Input validation
        if not selected_patient_id or not ultrasound_type:
            messages.error(request, "Patient and Ultrasound Type are required fields.")
            context = {'patient': patient, 'patients': patients}
            return render(request, 'radiology/ultrasound_create.html', context)

        try:
            selected_patient = get_object_or_404(Patient_register, id=selected_patient_id)
        except Patient_register.DoesNotExist:
            messages.error(request, "Selected patient does not exist.")
            context = {'patient': patient, 'patients': patients}
            return render(request, 'radiology/ultrasound_create.html', context)
        except Exception as e:
            messages.error(request, f"An error occurred fetching patient: {e}")
            context = {'patient': patient, 'patients': patients}
            return render(request, 'radiology/ultrasound_create.html', context)


        # Re-fetch active bill for the *selected* patient, in case patient_id was not initially provided
        # or if the patient was changed in the form.
        current_active_bill = get_active_bill_for_patient(selected_patient)
        if not current_active_bill:
            messages.error(request, "No active bill found for the selected patient. Cannot create ultrasound record. Please create a bill or re-admit the patient.")
            context = {'patient': selected_patient, 'patients': patients} # Pass selected_patient for form
            return render(request, 'radiology/ultrasound_create.html', context)

        try:
            with transaction.atomic():
                ultrasound_obj = Ultrasound.objects.create(
                    patient=selected_patient,
                    ultrasound_type=ultrasound_type,
                    findings=findings,
                    image=image,
                    bill=current_active_bill # Assign the active bill here
                )

                # Update the active bill's ultrasound_charge
                if not current_active_bill.details:
                    current_active_bill.details = {} # Ensure 'details' dictionary exists

                current_ultrasound_charge = Decimal(str(current_active_bill.details.get('ultrasound_charge', 0.0)))
                ultrasound_cost = ultrasound_obj.price # Assuming Ultrasound model has a 'price' field
                current_active_bill.details['ultrasound_charge'] = float(current_ultrasound_charge + ultrasound_cost)

                # Recalculate total_amount and due_amount for the bill
                current_active_bill.total_amount = Decimal(str(current_active_bill.total_amount)) + ultrasound_cost
                current_active_bill.due_amount = Decimal(str(current_active_bill.due_amount)) + ultrasound_cost # Assuming no payment applied yet

                current_active_bill.save(update_fields=['details', 'total_amount', 'due_amount'])

            messages.success(request, f"Ultrasound for {selected_patient.name} ({ultrasound_obj.ultrasound_type}) created and bill updated.")
            return redirect('ultrasound_detail', ultrasound_id=ultrasound_obj.id)

        except Exception as e:
            logger.exception(f"Error creating ultrasound or updating bill for patient {selected_patient.id}: {e}")
            messages.error(request, f"An error occurred while creating ultrasound and updating bill: {e}")
            context = {'patient': selected_patient, 'patients': patients}
            return render(request, 'radiology/ultrasound_create.html', context)

    context = {
        'patient': patient, # Will be None if not passed in URL
        'patients': patients, # For dropdown selection
    }
    return render(request, 'radiology/ultrasound_create.html', context)


    
def ultrasound_update(request, ultrasound_id):
    try:
        ultrasound = Ultrasound.objects.get(id=ultrasound_id)
    except Ultrasound.DoesNotExist:
        return render(request, 'radiology/ultrasound_error.html', {'error': 'Ultrasound does not exist.'})
    if request.method == 'POST':
        ultrasound_type = request.POST.get('ultrasound_type', ultrasound.ultrasound_type)
        findings = request.POST.get('findings', ultrasound.findings)
        image = request.FILES.get('image', ultrasound.image)
        
        ultrasound.ultrasound_type = ultrasound_type
        ultrasound.findings = findings
        if image:
            ultrasound.image = image
        ultrasound.save()
        
        return render(request, 'radiology/ultrasound_success.html', {'ultrasound': ultrasound})
    else:
        context = {
            'ultrasound': ultrasound
        }
        return render(request, 'radiology/ultrasound_update.html', context)

def ultrasound_delete(request, ultrasound_id):
    try:
        ultrasound = Ultrasound.objects.get(id=ultrasound_id)
    except Ultrasound.DoesNotExist:
        return render(request, 'radiology/ultrasound_error.html', {'error': 'Ultrasound does not exist.'})
    
    if request.method == 'POST':
        ultrasound.delete()
        return render(request, 'radiology/ultrasound_success.html', {'message': 'Ultrasound deleted successfully.'})
    
    context = {
        'ultrasound': ultrasound
    }
    return render(request, 'radiology/ultrasound_delete.html', context)

def ultrasound_detail(request, ultrasound_id):
    try:
        ultrasound = Ultrasound.objects.get(id=ultrasound_id)
    except Ultrasound.DoesNotExist:
        return render(request, 'radiology/ultrasound_error.html', {'error': 'Ultrasound does not exist.'})
    
    context = {
        'ultrasound': ultrasound
    }
    return render(request, 'radiology/ultrasound_detail.html', context)




def ultrasound_requests_list(request):
    requests = UltrasoundRequest.objects.filter(is_completed=False).order_by('-request_date')
    return render(request, 'radiology/ultrasound_requests.html', {'requests': requests})

def add_ultrasound_for_request(request, request_id):
    us_request = get_object_or_404(UltrasoundRequest, id=request_id)
    patient = us_request.patient
    if request.method == 'POST':
        ultrasound_type = request.POST.get('ultrasound_type')
        findings = request.POST.get('findings')
        image = request.FILES.get('image')
        ultrasound = Ultrasound.objects.create(
            patient=patient,
            ultrasound_type=ultrasound_type,
            findings=findings,
            image=image
        )
        us_request.is_completed = True
        us_request.save()
        return redirect('ultrasound_detail', ultrasound_id=ultrasound.id)
    return render(request, 'radiology/add_ultrasound_for_request.html', {'patient': patient, 'us_request': us_request})

def reject_ultrasound_request(request, request_id):
    us_request = get_object_or_404(UltrasoundRequest, id=request_id)
    if request.method == 'POST':
        us_request.is_completed = True
        us_request.notes = (us_request.notes or '') + "\nRejected by doctor."
        us_request.save()
        return redirect('ultrasound_requests_list')
    return redirect('ultrasound_requests_list')

def radiology_dashboard(request):
    ultrasounds = Ultrasound.objects.all()
    pending_requests = UltrasoundRequest.objects.filter(is_completed=False)
    completed_requests = UltrasoundRequest.objects.filter(is_completed=True)
    context = {
        'ultrasounds': ultrasounds,
        'pending_requests': pending_requests,
        'completed_requests': completed_requests,
    }
    return render(request, 'radiology/radiology_dashboard.html', context)