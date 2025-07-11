from django.shortcuts import render,redirect
from .models import Drug, DrugIssue, OTCSale
from django.contrib.auth.decorators import login_required

# OTC Sale View (with search)
@login_required
def otc_sale(request):
    search_query = request.GET.get('search', '').strip()
    drugs = Drug.objects.filter(quantity__gt=0)
    if search_query:
        drugs = drugs.filter(name__icontains=search_query)

    if request.method == 'POST':
        drug_id = request.POST.get('drug')
        quantity = int(request.POST.get('quantity', 0))
        customer_name = request.POST.get('customer_name', '').strip()
        customer_contact = request.POST.get('customer_contact', '').strip()
        if not drug_id or quantity <= 0:
            messages.error(request, "Please select a drug and enter a valid quantity.")
            return render(request, 'drugs/otc_sale.html', {'drugs': drugs})
        try:
            drug = Drug.objects.get(id=drug_id)
        except Drug.DoesNotExist:
            messages.error(request, "Selected drug does not exist.")
            return render(request, 'drugs/otc_sale.html', {'drugs': drugs})
        if drug.quantity < quantity:
            messages.error(request, f"Insufficient stock for {drug.name}. Available: {drug.quantity}")
            return render(request, 'drugs/otc_sale.html', {'drugs': drugs})
        total_price = drug.price * quantity
        sale = OTCSale.objects.create(
            drug=drug,
            quantity=quantity,
            price_per_unit=drug.price,
            total_price=total_price,
            customer_name=customer_name,
            customer_contact=customer_contact,
            cashier=request.user
        )
        drug.quantity -= quantity
        drug.save()
        messages.success(request, f"Sold {quantity} x {drug.name} for KSH {total_price}.")
        return redirect('otc_sales_list')
    return render(request, 'drugs/otc_sale.html', {'drugs': drugs})

# OTC Sales List View
@login_required
def otc_sales_list(request):
    sales = OTCSale.objects.all().order_by('-sale_datetime')
    return render(request, 'drugs/otc_sales_list.html', {'sales': sales})
from django.contrib import messages
from patients.models import Billing, Patient_register
from django.db.models import Q


def all_drugs(request):
    drugs = Drug.objects.all()
    return render(request, 'drugs/home.html', {'drugs': drugs})
def add_drug(request): 
    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        expiry_date = request.POST.get('expiry_date')
        price = request.POST.get('price')

        # Validate required fields
        if not all([name, quantity, expiry_date, price]):
            messages.error(request,"All fields are required.")
            return render(request, 'drugs/add_drug.html')

        # Check for duplicate drug
        if Drug.objects.filter(name=name).exists():
            messages.error(request,"Drug with this name already exists.")
            return render(request, 'drugs/add_drug.html')

        # Create and save the new drug
        new_drug = Drug(name=name, quantity=quantity, expiry_date=expiry_date, price=price)
        new_drug.save()

        # Redirect or return success response
        messages.success(request, "Drug successfully added.")
        return redirect(all_drugs)  # Replace 'success_page' with your actual success URL

        # If GET request, render the registration form
    return render(request, 'drugs/add_drug.html')  

def drug_update(request, id):
    drug = Drug.objects.get(id=id)
    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        expiry_date = request.POST.get('expiry_date')
        price = request.POST.get('price')

        # Validate required fields
        if not all([name, quantity, expiry_date, price]):
            messages.error(request,"All fields are required.")
            return render(request, 'drugs/update_drug.html', {'drug': drug})

        # Check for duplicate drug
        if Drug.objects.filter(name=name).exclude(id=id).exists():
            messages.error(request,"Drug with this name already exists.")
            return render(request, 'drugs/update_drug.html', {'drug': drug})

        # Update the drug details
        drug.name = name
        drug.quantity = quantity
        drug.expiry_date = expiry_date
        drug.price = price
        drug.save()

        # Redirect or return success response
        messages.success(request, "Drug successfully updated.")
        return redirect(all_drugs)  # Replace 'success_page' with your actual success URL

    # If GET request, render the update form
    return render(request, 'drugs/update_drug.html', {'drug': drug})  # Replace with your actual template path
def drug_delete(request, id):
    drug = Drug.objects.get(id=id)
    if request.method == 'POST':
        drug.delete()
        messages.success(request, "Drug successfully deleted.")
        return redirect(all_drugs)  # Replace 'success_page' with your actual success URL

    # If GET request, render the delete confirmation page
    return render(request, 'drugs/delete_drug.html', {'drug': drug})  # Replace with your actual template path
def drug_search(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        drugs = Drug.objects.filter(name__icontains=name)
        if not drugs.exists():
            messages.error(request,"No drugs found with this name.")
            return render(request, 'drugs/search_drug.html')

        return render(request, 'drugs/search_drug.html', {'drugs': drugs})

    return render(request, 'drugs/search_drug.html')  
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

        # Check if sufficient quantity is available
        if drug.quantity < int(quantity_issued):
            messages.error(request,"Insufficient quantity available \nCheck the remaining stock.")
            return render(request, 'drugs/issue_drug.html')

        # Create and save the drug issue record
        drug_issue = DrugIssue(drug=drug, quantity_issued=quantity_issued)
        drug_issue.save()

        # Update the drug quantity
        drug.quantity -= int(quantity_issued)
        drug.save()

        # Redirect or return success response
        messages.success(request, "Drug successfully issued.")
        return redirect(all_drugs)  
    drugs = Drug.objects.all()
    return render(request, 'drugs/issue_drug.html', {'drugs': drugs})  

def stock_out_warning(request):
    # Get all drugs that are out of stock
    out_of_stock_drugs = Drug.objects.filter(quantity=0)
    
    # Check if any drugs are out of stock
    if out_of_stock_drugs.exists():
        for drug in out_of_stock_drugs:
            # Send a warning message for each out of stock drug
            messages.warning(request, f"{drug.name} is out of stock.")

    
    return render(request, 'drugs/stock_out_warning.html', {'out_of_stock_drugs': out_of_stock_drugs})

def pharmacy_dashboard(request):
    """
    Modern pharmacy dashboard: shows all drugs, prescribed drugs, issued drugs, and allows marking as given/not given.
    Integrates with billing to update charges and payment status.
    """
   
    # All drugs in stock
    drugs = Drug.objects.all()
    # All prescriptions (DrugIssue) that are not yet marked as given
    pending_issues = DrugIssue.objects.filter(given=False)
    # All issued drugs (history)
    issued_drugs = DrugIssue.objects.filter(given=True)

    # OTC sales summary for today
    from datetime import datetime, timedelta
    from django.utils import timezone
    today = timezone.localdate()
    otc_sales_today = OTCSale.objects.filter(sale_datetime__date=today)
    otc_sales_today_count = otc_sales_today.count()
    from django.db.models import Sum
    otc_sales_today_total = otc_sales_today.aggregate(Sum('total_price'))['total_price__sum'] or 0

    # Handle marking as given or not given
    if request.method == 'POST':
        action = request.POST.get('action')
        issue_id = request.POST.get('issue_id')
        if action == 'mark_given' and issue_id:
            try:
                issue = DrugIssue.objects.get(id=issue_id)
                issue.given = True
                issue.save()
                # Remove from bill charges if not given
                # Find the bill for this patient
                bill = Billing.objects.filter(patient=issue.patient).last()
                if bill:
                    # Remove this drug's charge from bill.details and recalculate
                    details = bill.details or {}
                    med_charge = details.get('medication_charge', 0)
                    med_charge -= float(issue.drug.price) * int(issue.quantity_issued)
                    details['medication_charge'] = max(med_charge, 0)
                    # Recalculate total
                    details['total'] = sum([
                        float(details.get('consultation_charge', 0)),
                        float(details.get('room_charge', 0)),
                        float(details.get('medication_charge', 0)),
                        float(details.get('laboratory_charge', 0)),
                        float(details.get('ultrasound_charge', 0)),
                    ])
                    bill.details = details
                    bill.total_amount = details['total']
                    bill.save()
                messages.success(request, 'Drug marked as given and bill updated.')
            except DrugIssue.DoesNotExist:
                messages.error(request, 'Drug issue not found.')
        elif action == 'mark_not_given' and issue_id:
            try:
                issue = DrugIssue.objects.get(id=issue_id)
                issue.given = False
                issue.save()
                # Add back to bill charges
                bill = Billing.objects.filter(patient=issue.patient).last()
                if bill:
                    details = bill.details or {}
                    med_charge = details.get('medication_charge', 0)
                    med_charge += float(issue.drug.price) * int(issue.quantity_issued)
                    details['medication_charge'] = med_charge
                    details['total'] = sum([
                        float(details.get('consultation_charge', 0)),
                        float(details.get('room_charge', 0)),
                        float(details.get('medication_charge', 0)),
                        float(details.get('laboratory_charge', 0)),
                        float(details.get('ultrasound_charge', 0)),
                    ])
                    bill.details = details
                    bill.total_amount = details['total']
                    bill.save()
                messages.success(request, 'Drug marked as not given and bill updated.')
            except DrugIssue.DoesNotExist:
                messages.error(request, 'Drug issue not found.')
        elif action == 'mark_bill_paid':
            bill_id = request.POST.get('bill_id')
            try:
                bill = Billing.objects.get(id=bill_id)
                bill.is_paid = True
                bill.status = 'paid'
                bill.save()
                messages.success(request, 'Bill marked as paid.')
            except Billing.DoesNotExist:
                messages.error(request, 'Bill not found.')
        return redirect('pharmacy_dashboard')

    # For dashboard display: show all bills with outstanding medication charges
    bills = Billing.objects.filter(details__medication_charge__gt=0)
    context = {
        'drugs': drugs,
        'pending_issues': pending_issues,
        'issued_drugs': issued_drugs,
        'bills': bills,
        'otc_sales_today_count': otc_sales_today_count,
        'otc_sales_today_total': otc_sales_today_total,
    }
    return render(request, 'drugs/pharmacy_dashboard.html', context)