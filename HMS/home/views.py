from django.shortcuts import render
from patients.models import Patient_register
from drugs.models import Drug, DrugIssue

def dashboard(request):
    # Summary data
    total_patients = Patient_register.objects.count()
    total_drugs = Drug.objects.count()
    total_drug_issues = DrugIssue.objects.count()

    # Recent activities
    recent_patients = Patient_register.objects.order_by('-adm_date')[:5]
    recent_drug_issues = DrugIssue.objects.order_by('-issue_date')[:5]

    context = {
        'total_patients': total_patients,
        'total_drugs': total_drugs,
        'total_drug_issues': total_drug_issues,
        'recent_patients': recent_patients,
        'recent_drug_issues': recent_drug_issues,
    }
    return render(request, 'home/dashboard.html', context)

def landing(request):
    return render(request, 'home/landing.html')
