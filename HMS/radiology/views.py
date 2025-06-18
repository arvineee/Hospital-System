from django.shortcuts import render, get_object_or_404, redirect
from .models import Ultrasound, UltrasoundRequest
from patients.models import Patient_register
from django.views.decorators.http import require_POST


# Create your views here.

def ultrasound_list(request):
    ultrasounds = Ultrasound.objects.all()
    context = {
        'ultrasounds': ultrasounds
    }
    return render(request, 'radiology/ultrasound_list.html', context)


def ultrasound_create(request, patient_id=None):
    # Support patient_id from URL or GET param (for requests from patients)
    if not patient_id:
        patient_id = request.GET.get('patient_id')

    patient = None
    patients = None

    if patient_id:
        patient = get_object_or_404(Patient_register, id=patient_id)

    if request.method == 'POST':
        # Patient from hidden field or dropdown
        if patient:
            selected_patient = patient
        else:
            selected_patient_id = request.POST.get('patient_id')
            if not selected_patient_id:
                return render(request, 'radiology/ultrasound_error.html', {'error': 'Patient ID is required.'})
            selected_patient = get_object_or_404(Patient_register, id=selected_patient_id)

        ultrasound_type = request.POST.get('ultrasound_type')
        findings = request.POST.get('findings')
        image = request.FILES.get('image')

        if not ultrasound_type:
            return render(request, 'radiology/ultrasound_error.html', {'error': 'Ultrasound type is required.'})

        ultrasound = Ultrasound(
            patient=selected_patient,
            ultrasound_type=ultrasound_type,
            findings=findings,
            image=image
        )
        ultrasound.save()

        # If this was a request, mark it as completed
        us_request = UltrasoundRequest.objects.filter(patient=selected_patient, is_completed=False).first()
        if us_request:
            us_request.is_completed = True
            us_request.save()

        return render(request, 'radiology/ultrasound_success.html', {'ultrasound': ultrasound})

    else:
        if not patient:
            patients = Patient_register.objects.all()
        context = {
            'patient': patient,
            'patients': patients
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
    requests = UltrasoundRequest.objects.filter(is_completed=False).order_by('-requested_at')
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