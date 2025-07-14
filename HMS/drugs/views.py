from django.shortcuts import render,redirect
from .models import Drug, DrugIssue, OTCSale
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
import logging

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
from patients.views import get_active_bill_for_patient


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
def drug_issue(request, patient_id):
    """
    Handles the creation of a new drug issue for a patient.
    Assigns the drug issue to the patient's active bill and updates the bill's medication charge.
    """
    patient = get_object_or_404(Patient_register, id=patient_id)
    drugs = Drug.objects.filter(quantity__gt=0).order_by('name') # Only show drugs in stock

    if request.method == 'POST':
        drug_id = request.POST.get('drug')
        quantity_str = request.POST.get('quantity_issued')

        # Basic input validation
        if not drug_id or not quantity_str:
            messages.error(request, "Please select a drug and enter a quantity.")
            # Pass existing context back on error to repopulate form
            context = {'patient': patient, 'drugs': drugs}
            return render(request, 'drugs/drug_issue_create.html', context)

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                messages.error(request, "Quantity must be a positive number.")
                context = {'patient': patient, 'drugs': drugs}
                return render(request, 'drugs/drug_issue_create.html', context)

            drug = get_object_or_404(Drug, id=drug_id)
        except (ValueError, Drug.DoesNotExist):
            messages.error(request, "Invalid drug or quantity provided.")
            context = {'patient': patient, 'drugs': drugs}
            return render(request, 'drugs/drug_issue_create.html', context)

        if drug.quantity < quantity:
            messages.error(request, f"Insufficient stock for {drug.name}. Available: {drug.quantity}")
            context = {'patient': patient, 'drugs': drugs}
            return render(request, 'drugs/drug_issue_create.html', context)

        # Get the patient's active bill
        active_bill = get_active_bill_for_patient(patient)
        if not active_bill:
            messages.error(request, "No active bill found for this patient. Please ensure a bill is created or re-admit the patient if necessary.")
            return redirect('pat_view', id=patient.id) # Use id consistent with patient view URL

        # Perform the drug issue and bill update within an atomic transaction
        try:
            with transaction.atomic():
                # Create the DrugIssue record
                DrugIssue.objects.create(
                    drug=drug,
                    patient=patient,
                    quantity_issued=quantity,
                    bill=active_bill,  # Link to the active bill
                    given=False, # Mark as not yet given (e.g., pending pharmacy dispensing)
                )

                # Update drug quantity in stock
                drug.quantity -= quantity
                drug.save(update_fields=['quantity'])

                # Update the active bill's medication_charge
                if not active_bill.details:
                    active_bill.details = {} # Ensure 'details' dictionary exists
                
                # Get current medication charge safely, convert to Decimal for calculation
                current_med_charge = Decimal(str(active_bill.details.get('medication_charge', 0.0)))
                item_cost = drug.price * Decimal(quantity)
                
                active_bill.details['medication_charge'] = float(current_med_charge + item_cost)

                # Recalculate total_amount and due_amount for the bill
                # It's important to use Decimal for financial calculations
                active_bill.total_amount = Decimal(str(active_bill.total_amount)) + item_cost
                active_bill.due_amount = Decimal(str(active_bill.due_amount)) + item_cost # Assuming no payment applied yet

                active_bill.save(update_fields=['details', 'total_amount', 'due_amount'])

            messages.success(request, f"{quantity} of {drug.name} issued to {patient.name} and bill updated.")
            return redirect('pat_view', id=patient.id) # Redirect back to patient profile

        except Exception as e:
            logging.logger.exception(f"Error issuing drug or updating bill for patient {patient.id}: {e}")
            messages.error(request, f"An error occurred while issuing drug and updating bill: {e}")
            # Redirect to prevent double submission
            return redirect('drug_issue_create', patient_id=patient.id)


    context = {
        'patient': patient,
        'drugs': drugs,
    }
    return render(request, 'drugs/drug_issue_create.html', context)


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