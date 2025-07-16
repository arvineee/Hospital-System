from django.shortcuts import render,redirect
from .models import Drug, DrugIssue, OTCSale
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
import logging
from .models import Drug, DrugIssue, OTCSale, Prescription, PrescriptionItem, DrugSupplier, DrugOrder, DrugOrderItem,StockAdjustment
from patients.models import Patient_register, Billing 
from datetime import timedelta
from django.db.models import F
from django.http import JsonResponse
from patients.views import get_active_bill_for_patient
from django.db.models import Sum

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
@login_required
def add_drug(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = int(request.POST.get('quantity'))
        expiry_date = request.POST.get('expiry_date')
        price = Decimal(request.POST.get('price'))
        reorder_level = int(request.POST.get('reorder_level', 10))
        unit_of_measure = request.POST.get('unit_of_measure', 'tablets')

        # Basic validation
        if not all([name, quantity, expiry_date, price]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'drugs/add_drug.html')

        try:
            Drug.objects.create(
                name=name,
                quantity=quantity,
                expiry_date=expiry_date,
                price=price,
                reorder_level=reorder_level,
                unit_of_measure=unit_of_measure
            )
            messages.success(request, f"Drug '{name}' added successfully.")
            return redirect('drug_list_and_alerts')
        except Exception as e:
            messages.error(request, f"Error adding drug: {e}")

    return render(request, 'drugs/add_drug.html')



@login_required
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


@login_required
def get_stock_warnings(request):
    """
    Returns a JSON response with a list of drugs that are out of stock
    or below their reorder level.
    """
    low_stock_drugs = list(Drug.objects.filter(quantity__lte=F('reorder_level')).values('name', 'quantity', 'reorder_level')) # cite: uploaded:models.py
    
    out_of_stock_drugs = list(Drug.objects.filter(quantity=0).values('name')) # cite: uploaded:models.py

    expiring_soon_drugs_objects = Drug.objects.filter(expiry_date__lte=timezone.now().date() + timedelta(days=90)).exclude(quantity=0) # cite: uploaded:models.py
    expiring_soon_drugs = [{'name': drug.name, 'expiry_date': drug.expiry_date.strftime('%Y-%m-%d')} for drug in expiring_soon_drugs_objects] # cite: uploaded:models.py

    warnings = {
        'low_stock': low_stock_drugs,
        'out_of_stock': out_of_stock_drugs,
        'expiring_soon': expiring_soon_drugs,
    }
    return JsonResponse(warnings)

def pharmacy_dashboard(request):
    """
    Modern pharmacy dashboard: shows all drugs, prescribed drugs, issued drugs,
    and allows marking as given/not given. Integrates with billing to update
    charges and payment status.
    """
    # All drugs in stock
    drugs = Drug.objects.all() # cite: uploaded:views.py

    # All prescriptions that are not yet fulfilled
    unfulfilled_prescriptions = Prescription.objects.filter(is_fulfilled=False).order_by('prescription_date') # cite: uploaded:views.py

    # All prescriptions (DrugIssue) that are not yet marked as given
    pending_issues = DrugIssue.objects.filter(given=False) # cite: uploaded:views.py

    # All issued drugs (history)
    issued_drugs = DrugIssue.objects.filter(given=True) # cite: uploaded:views.py

    # OTC sales summary for today
    today = timezone.localdate()
    otc_sales_today = OTCSale.objects.filter(sale_datetime__date=today) # cite: uploaded:views.py
    otc_sales_today_count = otc_sales_today.count() # cite: uploaded:views.py
    otc_sales_today_total = otc_sales_today.aggregate(Sum('total_price'))['total_price__sum'] or 0 # cite: uploaded:views.py

    # Handle marking as given or not given
    if request.method == 'POST':
        action = request.POST.get('action')
        issue_id = request.POST.get('issue_id')

        if action == 'mark_given' and issue_id:
            try:
                issue = DrugIssue.objects.get(id=issue_id) # cite: uploaded:views.py
                issue.given = True # cite: uploaded:views.py
                issue.save() # cite: uploaded:views.py

                # Find the bill for this patient
                bill = Billing.objects.filter(patient=issue.patient).last() # cite: uploaded:views.py
                if bill:
                    details = bill.details or {}
                    med_charge = details.get('medication_charge', 0)
                    med_charge -= float(issue.drug.price) * int(issue.quantity_issued)
                    details['medication_charge'] = max(med_charge, 0)
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
                messages.success(request, 'Drug marked as given and bill updated.') # cite: uploaded:views.py
            except DrugIssue.DoesNotExist:
                messages.error(request, 'Drug issue not found.') # cite: uploaded:views.py
        elif action == 'mark_not_given' and issue_id:
            try:
                issue = DrugIssue.objects.get(id=issue_id) # cite: uploaded:views.py
                issue.given = False # cite: uploaded:views.py
                issue.save() # cite: uploaded:views.py
                
                # Add back to bill charges
                bill = Billing.objects.filter(patient=issue.patient).last() # cite: uploaded:views.py
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
                messages.success(request, 'Drug marked as not given and bill updated.') # cite: uploaded:views.py
            except DrugIssue.DoesNotExist:
                messages.error(request, 'Drug issue not found.') # cite: uploaded:views.py

    context = {
        'drugs': drugs, # cite: uploaded:views.py
        'unfulfilled_prescriptions': unfulfilled_prescriptions, # cite: uploaded:views.py
        'pending_issues': pending_issues, # cite: uploaded:views.py
        'issued_drugs': issued_drugs, # cite: uploaded:views.py
        'otc_sales_today_count': otc_sales_today_count, # cite: uploaded:views.py
        'otc_sales_today_total': otc_sales_today_total, # cite: uploaded:views.py
        # Stock warnings will be fetched asynchronously
    }
    return render(request, 'drugs/pharmacy_dashboard.html', context) # cite: uploaded:pharmacy_dashboard.html

@login_required
def drug_list_and_alerts(request):
    search_query = request.GET.get('search', '').strip()
    drugs = Drug.objects.all().order_by('name')

    if search_query:
        drugs = drugs.filter(name__icontains=search_query)

    low_stock_drugs = [drug for drug in drugs if drug.is_low_stock]
    expiring_drugs = [drug for drug in drugs if drug.is_expiring_soon] # within 90 days

    context = {
        'drugs': drugs,
        'low_stock_drugs': low_stock_drugs,
        'expiring_drugs': expiring_drugs,
        'search_query': search_query,
    }
    return render(request, 'drugs/drug_list_alerts.html', context)

@login_required
def create_prescription(request, patient_id):
    """
    Allows a doctor to create a new e-prescription for a patient.
    """
    patient = get_object_or_404(Patient_register, id=patient_id)
    drugs = Drug.objects.filter(quantity__gt=0).order_by('name')
    
    if request.method == 'POST':
        # This is a simplified version. For a real-world scenario, you'd use Django Forms/Formsets.
        drug_ids = request.POST.getlist('drug')
        dosages = request.POST.getlist('dosage')
        frequencies = request.POST.getlist('frequency')
        durations = request.POST.getlist('duration')
        notes = request.POST.get('notes')

        if not drug_ids:
            messages.error(request, "Please add at least one drug to the prescription.")
            return render(request, 'drugs/create_prescription.html', {'patient': patient, 'drugs': drugs})

        try:
            with transaction.atomic():
                prescription = Prescription.objects.create(
                    patient=patient,
                    prescribed_by=request.user,
                    notes=notes
                )
                
                for i in range(len(drug_ids)):
                    drug = Drug.objects.get(id=drug_ids[i])
                    PrescriptionItem.objects.create(
                        prescription=prescription,
                        drug=drug,
                        dosage=dosages[i],
                        frequency=frequencies[i],
                        duration=durations[i]
                    )
                
            messages.success(request, f"Prescription created successfully for {patient.name}.")
            return redirect('patient_prescriptions', patient_id=patient.id)
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")

    context = {
        'patient': patient,
        'drugs': drugs
    }
    return render(request, 'drugs/create_prescription.html', context)

@login_required
def patient_prescriptions(request, patient_id):
    """
    Lists all prescriptions for a specific patient.
    """
    patient = get_object_or_404(Patient_register, id=patient_id)
    prescriptions = Prescription.objects.filter(patient=patient).order_by('-prescription_date')
    context = {
        'patient': patient,
        'prescriptions': prescriptions
    }
    return render(request, 'drugs/patient_prescriptions.html', context)

@login_required
def prescription_detail(request, prescription_id):
    """
    Displays the details of a single prescription.
    """
    prescription = get_object_or_404(Prescription.objects.prefetch_related('items__drug'), id=prescription_id)
    context = {
        'prescription': prescription
    }
    return render(request, 'drugs/prescription_detail.html', context)

# SUPPLIER MANAGEMENT
@login_required
def supplier_list(request):
    """
    Displays a list of all drug suppliers.
    """
    suppliers = DrugSupplier.objects.all()
    return render(request, 'drugs/supplier_list.html', {'suppliers': suppliers})

@login_required
def add_supplier(request):
    """
    Handles the creation of a new supplier.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_person = request.POST.get('contact_person')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        
        if not name:
            messages.error(request, "Supplier name is required.")
        else:
            DrugSupplier.objects.create(
                name=name,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address
            )
            messages.success(request, f"Supplier '{name}' added successfully.")
            return redirect('supplier_list')
            
    return render(request, 'drugs/add_supplier.html')

# INVENTORY RECONCILIATION
@login_required
def inventory_reconciliation(request):
    """
    Provides a tool to perform and log stock adjustments.
    """
    drugs = Drug.objects.all().order_by('name')
    if request.method == 'POST':
        drug_id = request.POST.get('drug_id')
        try:
            physical_count = int(request.POST.get('physical_count'))
            reason = request.POST.get('reason')
            drug = Drug.objects.get(id=drug_id)
            
            if physical_count < 0:
                messages.error(request, "Physical count cannot be negative.")
            else:
                initial_quantity = drug.quantity
                
                with transaction.atomic():
                    # Create a log of the adjustment
                    StockAdjustment.objects.create(
                        drug=drug,
                        user=request.user,
                        initial_quantity=initial_quantity,
                        new_quantity=physical_count,
                        reason=reason
                    )
                    
                    # Update the drug's quantity
                    drug.quantity = physical_count
                    drug.save()
                
                messages.success(request, f"Stock for {drug.name} has been reconciled.")
                return redirect('inventory_reconciliation')

        except (ValueError, TypeError):
            messages.error(request, "Invalid physical count entered.")
        except Drug.DoesNotExist:
            messages.error(request, "Drug not found.")
        
    return render(request, 'drugs/inventory_reconciliation.html', {'drugs': drugs})


# DRUG INTERACTION WARNINGS (Placeholder)
# A full implementation requires an external API or a comprehensive internal database.
# This is a conceptual placeholder.
def check_drug_interactions(drug_list):
    """
    Conceptual function for checking drug interactions.
    In a real application, this would call an external service.
    """
    # Dummy logic
    warnings = []
    drug_names = [drug.name.lower() for drug in drug_list]
    if 'warfarin' in drug_names and 'aspirin' in drug_names:
        warnings.append("High risk of bleeding: Warfarin and Aspirin should not be taken together without medical supervision.")
    return warnings
