from django.shortcuts import render
from .models import Ultrasound
from patients.models import Patient_register

# Create your views here.

def ultrasound_list(request):
    ultrasounds = Ultrasound.objects.all()
    context = {
        'ultrasounds': ultrasounds
    }
    return render(request, 'radiology/ultrasound_list.html', context)

def ultrasound_create(request, patient_id=None):
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        if not patient_id:
            return render(request, 'radiology/ultrasound_error.html', {'error': 'Patient ID is required.'})
        if not Patient_register.objects.filter(id=patient_id).exists():
            return render(request, 'radiology/ultrasound_error.html', {'error': 'Patient does not exist.'})
        patient = Patient_register.objects.get(id=patient_id)
        ultrasound_type = request.POST.get('ultrasound_type')
        findings = request.POST.get('findings')
        image = request.FILES.get('image')
        if not ultrasound_type:
            return render(request, 'radiology/ultrasound_error.html', {'error': 'Ultrasound type is required.'})
        ultrasound = Ultrasound(
            patient=patient,
            ultrasound_type=ultrasound_type,
            findings=findings,
            image=image
        )
        ultrasound.save()
        return render(request, 'radiology/ultrasound_success.html', {'ultrasound': ultrasound})
    else:
        patients = Patient_register.objects.all()
        context = {
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

