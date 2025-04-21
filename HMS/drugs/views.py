from django.shortcuts import render,redirect
from .models import Drug, DrugIssue
from django.contrib import messages


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