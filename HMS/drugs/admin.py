from django.contrib import admin
from .models import Drug, DrugIssue, OTCSale
# Register your models here.

@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ("name", "quantity", "expiry_date", "price")
    search_fields = ("name",)

@admin.register(DrugIssue)
class DrugIssueAdmin(admin.ModelAdmin):
    list_display = ("drug", "patient", "quantity_issued", "issue_date", "given")
    search_fields = ("drug__name", "patient__name")
    list_filter = ("given",)

@admin.register(OTCSale)
class OTCSaleAdmin(admin.ModelAdmin):
    list_display = ("drug", "quantity", "price_per_unit", "total_price", "sale_datetime", "customer_name", "cashier")
    search_fields = ("drug__name", "customer_name", "cashier__username")
    list_filter = ("sale_datetime",)

